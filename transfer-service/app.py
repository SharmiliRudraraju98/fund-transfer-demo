import os
from decimal import Decimal

import requests
from flasgger import Swagger
from flask import Flask, jsonify, request
from sqlalchemy import Column, DateTime, Integer, Numeric, String, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

app = Flask(__name__)
app.config["SWAGGER"] = {"title": "Transfer Service API", "uiversion": 3}
swagger = Swagger(app)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/appdb"
)
ACCOUNT_SERVICE_URL = os.environ.get("ACCOUNT_SERVICE_URL", "http://localhost:5001")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Transfer(Base):
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True)
    from_account_id = Column(Integer, nullable=False)
    to_account_id = Column(Integer, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    idempotency_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    


Base.metadata.create_all(engine)


@app.route("/health", methods=["GET"])
def health():
    """
    Health check
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is up
    """
    return jsonify({"status": "ok"}), 200


@app.route("/transfers", methods=["POST"])
def create_transfer():
    """
    Transfer funds between two accounts
    ---
    tags:
      - Transfers
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            from_account_id:
              type: integer
              example: 1
            to_account_id:
              type: integer
              example: 2
            amount:
              type: number
              example: 25
    responses:
      201:
        description: Transfer completed
        schema:
          type: object
          properties:
            id:
              type: integer
            status:
              type: string
      400:
        description: Debit failed, or credit failed and sender was refunded
    """
    data = request.get_json(force=True)
    from_id = data.get("from_account_id")
    to_id = data.get("to_account_id")
    amount = data.get("amount")
    idempotency_key = data.get("idempotency_key")

    if not all([from_id, to_id, amount]) or Decimal(str(amount)) <= 0:
        return jsonify({
            "error": "from_account_id, to_account_id, and a positive amount are required"
        }), 400

    session = SessionLocal()
    try:
        if idempotency_key:
            existing = (
                session.query(Transfer)
                .filter_by(idempotency_key=idempotency_key)
                .first()
            )
            if existing:
                return jsonify({
                    "id": existing.id,
                    "status": existing.status,
                    "duplicate": True,
                }), 200

        transfer = Transfer(
            from_account_id=from_id,
            to_account_id=to_id,
            amount=amount,
            status="pending",
            idempotency_key=idempotency_key,
        )
        session.add(transfer)
        session.commit()

        # Step 1: debit the sender
        debit_resp = requests.post(
            f"{ACCOUNT_SERVICE_URL}/accounts/{from_id}/debit", json={"amount": amount}
        )
        if debit_resp.status_code != 200:
            transfer.status = "failed"
            session.commit()
            return jsonify({"error": "debit failed", "detail": debit_resp.json()}), 400

        # Step 2: credit the receiver
        credit_resp = requests.post(
            f"{ACCOUNT_SERVICE_URL}/accounts/{to_id}/credit", json={"amount": amount}
        )
        if credit_resp.status_code != 200:
            # compensation: debit already happened, so refund the sender
            requests.post(
                f"{ACCOUNT_SERVICE_URL}/accounts/{from_id}/credit", json={"amount": amount}
            )
            transfer.status = "compensated"
            session.commit()
            return jsonify({
                "error": "credit failed, sender refunded",
                "detail": credit_resp.json(),
            }), 400

        transfer.status = "completed"
        session.commit()
        return jsonify({"id": transfer.id, "status": transfer.status}), 201
    finally:
        session.close()


@app.route("/transfers/<int:transfer_id>", methods=["GET"])
def get_transfer(transfer_id):
    """
    Get transfer status
    ---
    tags:
      - Transfers
    parameters:
      - in: path
        name: transfer_id
        type: integer
        required: true
    responses:
      200:
        description: Transfer found
      404:
        description: Transfer not found
    """
    session = SessionLocal()
    try:
        transfer = session.get(Transfer, transfer_id)
        if not transfer:
            return jsonify({"error": "transfer not found"}), 404
        return jsonify({
            "id": transfer.id,
            "from_account_id": transfer.from_account_id,
            "to_account_id": transfer.to_account_id,
            "amount": str(transfer.amount),
            "status": transfer.status,
            
        }), 200
    finally:
        session.close()


@app.route("/transfers", methods=["GET"])
def list_transfers():
    """
    List transfers, optionally filtered by account
    ---
    tags:
      - Transfers
    parameters:
      - in: query
        name: accountId
        type: integer
        required: false
    responses:
      200:
        description: List of transfers
    """
    account_id = request.args.get("accountId", type=int)
    session = SessionLocal()
    try:
        query = session.query(Transfer)
        if account_id:
            query = query.filter(
                (Transfer.from_account_id == account_id)
                | (Transfer.to_account_id == account_id)
            )
        transfers = query.all()
        return jsonify([
            {
                "id": t.id,
                "from_account_id": t.from_account_id,
                "to_account_id": t.to_account_id,
                "amount": str(t.amount),
                "status": t.status,
                "idempotency_key": t.idempotency_key,
            }
            for t in transfers
        ]), 200
    finally:
        session.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
