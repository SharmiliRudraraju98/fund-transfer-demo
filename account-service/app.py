import os
from decimal import Decimal

from flasgger import Swagger
from flask import Flask, jsonify, request
from sqlalchemy import Column, Integer, Numeric, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

app = Flask(__name__)
app.config["SWAGGER"] = {"title": "Account Service API", "uiversion": 3}
swagger = Swagger(app)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/appdb"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    balance = Column(Numeric(12, 2), nullable=False, default=0)


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


@app.route("/accounts", methods=["POST"])
def create_account():
    """
    Create a new account
    ---
    tags:
      - Accounts
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            initial_balance:
              type: number
              example: 100
    responses:
      201:
        description: Account created
        schema:
          type: object
          properties:
            id:
              type: integer
            balance:
              type: string
    """
    data = request.get_json(force=True)
    initial_balance = Decimal(str(data.get("initial_balance", 0)))

    session = SessionLocal()
    try:
        account = Account(balance=initial_balance)
        session.add(account)
        session.commit()
        return jsonify({"id": account.id, "balance": str(account.balance)}), 201
    finally:
        session.close()


@app.route("/accounts/<int:account_id>", methods=["GET"])
def get_account(account_id):
    """
    Get account balance
    ---
    tags:
      - Accounts
    parameters:
      - in: path
        name: account_id
        type: integer
        required: true
    responses:
      200:
        description: Account found
        schema:
          type: object
          properties:
            id:
              type: integer
            balance:
              type: string
      404:
        description: Account not found
    """
    session = SessionLocal()
    try:
        account = session.get(Account, account_id)
        if not account:
            return jsonify({"error": "account not found"}), 404
        return jsonify({"id": account.id, "balance": str(account.balance)}), 200
    finally:
        session.close()


@app.route("/accounts/<int:account_id>/debit", methods=["POST"])
def debit_account(account_id):
    """
    Debit an account
    ---
    tags:
      - Accounts
    parameters:
      - in: path
        name: account_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            amount:
              type: number
              example: 25
    responses:
      200:
        description: Debit successful
      400:
        description: Invalid amount or insufficient funds
      404:
        description: Account not found
    """
    data = request.get_json(force=True)
    amount = data.get("amount")
    if amount is None or Decimal(str(amount)) <= 0:
        return jsonify({"error": "amount must be positive"}), 400
    amount = Decimal(str(amount))

    session = SessionLocal()
    try:
        account = session.get(Account, account_id)
        if not account:
            return jsonify({"error": "account not found"}), 404
        if account.balance < amount:
            return jsonify({"error": "insufficient funds"}), 400
        account.balance -= amount
        session.commit()
        return jsonify({"id": account.id, "balance": str(account.balance)}), 200
    finally:
        session.close()


@app.route("/accounts/<int:account_id>/credit", methods=["POST"])
def credit_account(account_id):
    """
    Credit an account
    ---
    tags:
      - Accounts
    parameters:
      - in: path
        name: account_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            amount:
              type: number
              example: 25
    responses:
      200:
        description: Credit successful
      400:
        description: Invalid amount
      404:
        description: Account not found
    """
    data = request.get_json(force=True)
    amount = data.get("amount")
    if amount is None or Decimal(str(amount)) <= 0:
        return jsonify({"error": "amount must be positive"}), 400
    amount = Decimal(str(amount))

    session = SessionLocal()
    try:
        account = session.get(Account, account_id)
        if not account:
            return jsonify({"error": "account not found"}), 404
        account.balance += amount
        session.commit()
        return jsonify({"id": account.id, "balance": str(account.balance)}), 200
    finally:
        session.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
