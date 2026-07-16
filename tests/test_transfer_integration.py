import os
import uuid

import requests

ACCOUNT_SERVICE_URL = os.environ.get("ACCOUNT_SERVICE_URL", "http://localhost:5001")
TRANSFER_SERVICE_URL = os.environ.get("TRANSFER_SERVICE_URL", "http://localhost:5002")


def create_account(initial_balance):
    resp = requests.post(
        f"{ACCOUNT_SERVICE_URL}/accounts",
        json={"initial_balance": initial_balance},
        timeout=5,
    )
    assert resp.status_code == 201, f"failed to create account: {resp.text}"
    return resp.json()["id"]


def get_balance(account_id):
    resp = requests.get(f"{ACCOUNT_SERVICE_URL}/accounts/{account_id}", timeout=5)
    assert resp.status_code == 200, f"failed to fetch account: {resp.text}"
    return float(resp.json()["balance"])


def test_full_transfer_updates_both_balances():
    from_id = create_account(100)
    to_id = create_account(0)

    transfer_amount = 30
    idempotency_key = str(uuid.uuid4())

    resp = requests.post(
        f"{TRANSFER_SERVICE_URL}/transfers",
        json={
            "from_account_id": from_id,
            "to_account_id": to_id,
            "amount": transfer_amount,
            "idempotency_key": idempotency_key,
        },
        timeout=5,
    )

    assert resp.status_code == 201, f"transfer failed: {resp.text}"
    assert resp.json()["status"] == "completed"

    from_balance = get_balance(from_id)
    to_balance = get_balance(to_id)

    assert from_balance == 100 - transfer_amount, f"sender balance wrong: {from_balance}"
    assert to_balance == 0 + transfer_amount, f"receiver balance wrong: {to_balance}"