"""Generate deterministic CloudNine fixture DML. Run from any directory."""
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import random
import sqlite3

SQL = Path(__file__).resolve().parents[1] / "sql/milestone2"
START = "2026-05-01 00:00:00"
PRICE_CHANGE = "2026-08-01 00:00:00"
ATLAS = "Atlas Analytics / September"
RAND = random.Random(604)


def timestamp(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")


class Fixture:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript((SQL / "01_schema.sql").read_text())
        self.db.execute("BEGIN")
        self.dml = []
        self.invoices = {}
        self.invoice_balances = defaultdict(int)

    def run(self, sql, *args):
        # Trace only expanded fixture statements. Emit a portable plain SQL seed file.
        statements = []
        self.db.set_trace_callback(statements.append)
        try:
            row_id = self.db.execute(sql, args).lastrowid
        finally:
            self.db.set_trace_callback(None)
        self.dml.append(statements[0] + ";")
        return row_id

    def add(self, table, *values):
        placeholders = ", ".join("?" for _ in values)
        return self.run(f"INSERT INTO {table} VALUES ({placeholders})", *values)

    def invoice(self, payer, month, draft):
        key = payer, month, draft
        if key not in self.invoices:
            due = timestamp(datetime(2026, month + 1, 25))
            self.invoices[key] = self.add("invoice", None, payer, None, due, "draft")
        return self.invoices[key]

    def shares(self, charge, amount, payer, month, draft, split):
        sponsor_amount = round(abs(amount) * 0.4) * (-1 if amount < 0 else 1) if split else 0
        shares = [(payer, amount - sponsor_amount)]
        if sponsor_amount:
            shares.append((2, sponsor_amount))
        for account, portion in shares:
            invoice = self.invoice(account, month, draft)
            self.add("charge_share", None, charge, invoice, portion)
            self.invoice_balances[invoice] += portion


def reference_data(f):
    for region, (name, cities) in enumerate((
        ("US East", ("Ashburn", "Newark", "Boston")),
        ("US West", ("Portland", "San Jose", "Seattle")),
        ("EU Central", ("Frankfurt", "Amsterdam", "Dublin")),
    ), 1):
        f.add("region", region, name, "Regional data residency")
        f.add("availability_zone", 2 * region - 1, region, name + " A", "Dual utility feeds", "Private backbone")
        f.add("availability_zone", 2 * region, region, name + " B", "Independent utility feeds", "Private backbone")
        for local, city in enumerate(cities):
            f.add("data_center", 3 * (region - 1) + local + 1,
                  2 * region - 1 + (local == 2), city + " DC", city)

    services = (
        ("Compute", "Batch analytics and APIs", "vCPU-hours", (16, 64, 500, 10), 45, 50),
        ("Block Storage", "Databases and backups", "GiB-days", (0, 0, 4000, 5), 3, 3),
        ("Network Egress", "Outbound data transfer", "GB", (0, 0, 0, 40), 8, 9),
    )
    for kind, (name, note, unit, capacity, old, new) in enumerate(services, 1):
        f.add("resource_type", kind, name, note)
        f.add("service", kind, name, ("compute", "storage", "network")[kind - 1], unit)
        f.add("service_rate", 2 * kind - 1, kind, START, PRICE_CHANGE, old)
        f.add("service_rate", 2 * kind, kind, PRICE_CHANGE, None, new)
        for dc in range(1, 10):
            for slot in range(4):
                factor = 2 if slot == 3 else 1
                f.add("resource", resource_id(dc, kind, slot), kind, dc,
                      f"{('CMP', 'STG', 'NET')[kind - 1]}-{slot + 1:02}",
                      "high-capacity" if factor == 2 else "standard",
                      *(value * factor for value in capacity))

    names = (
        "Atlas Labs", "Northstar Research Foundation", "Cedar Health", "Harbor Commerce",
        "Signal Media", "Juniper Robotics", "Orbit Transit", "Ivy Financial",
        "Redwood Climate", "Mariner Bioinformatics", "Slate Education", "Quartz Security",
        "Willow Analytics", "Bluebird Games", "Halcyon Energy", "Beacon Logistics",
        "Northstar Imaging", "Northstar Genomics", "Cedar Clinical Analytics", "Orbit Route Lab",
        "Mira Chen", "Alex Rivera", "Sam Lee", "Jordan Patel",
    )
    for client, name in enumerate(names, 1):
        parent = {17: 2, 18: 2, 19: 3, 20: 7}.get(client)
        kind = "organization" if client <= 16 else "team" if client <= 20 else "individual"
        f.add("client", client, parent, name, kind, f"contact{client}@example.com", None)
        f.add("user_account", client, client, f"{name} contact", f"user{client}@example.com",
              "client", None, "active")
        f.add("billing_account", client, client, name + " Billing", client)
    for user, name, role in ((25, "Riley Morgan", "operations"), (26, "Casey Park", "billing")):
        f.add("user_account", user, None, name, f"staff{user}@example.com", "staff", role, "active")


def resource_id(dc, kind, slot):
    return (dc - 1) * 12 + (kind - 1) * 4 + slot + 1


def incidents(f):
    # Two planned maintenance events and at least one failure each month.
    events = defaultdict(list)
    outages = set()
    for month in range(5, 11):
        for dc in (2, 6):
            start = datetime(2026, month, 14, 20)
            events[resource_id(dc, 1, 3)].append((start, start + timedelta(hours=8),
                                                   "maintenance", "Firmware rollout"))
        for dc in (1, 4, 8)[:1 + (month - 5) // 2]:
            wave = 1 if dc == 1 else 2 if dc == 4 else 3
            start = datetime(2026, month, 2 + wave * 7) + timedelta(days=1)
            events[resource_id(dc, 1, 0)].append((start, start + timedelta(days=1),
                                                   "failed", "Hardware failure"))
            outages.add((month, dc, wave))
    for resource in range(1, 109):
        previous = START
        for start, end, state, reason in events[resource]:
            f.add("resource_state", None, resource, "usable", "In service", previous, timestamp(start), 25)
            f.add("resource_state", None, resource, state, reason, timestamp(start), timestamp(end), 25)
            previous = timestamp(end)
        f.add("resource_state", None, resource, "usable", "In service", previous, None, 25)
    return outages


def add_usage(f, subscription, allocation, kind, day, quantity, estimate, corrected=False, pending_meter=False):
    end = day + timedelta(days=1)
    period = timestamp(day), timestamp(end)
    # Genuine missing estimate cases. The focal usage always has a complete pair.
    if estimate is not None:
        f.add("usage_record", None, subscription, allocation, estimate, *period, "estimate",
              timestamp(day - timedelta(days=1)), None)
    if pending_meter:
        return None, None
    actual = f.add("usage_record", None, subscription, allocation,
                   max(0, quantity - 15) if corrected else quantity, *period, "actual",
                   timestamp(end + timedelta(hours=2)), None)
    if corrected:
        actual = f.add("usage_record", None, subscription, allocation, quantity, *period, "actual",
                       timestamp(end + timedelta(hours=3)), actual)
    rate, cents = {
        1: (2, 50) if day.month >= 8 else (1, 45),
        2: (4, 3) if day.month >= 8 else (3, 3),
        3: (6, 9) if day.month >= 8 else (5, 8),
    }[kind]
    amount = quantity * cents
    charge = f.add("charge", None, actual, None, rate, None, None, "metered", amount,
                   "posted", "Daily usage", timestamp(end + timedelta(hours=4)))
    return charge, amount


def work(f, month, dc, wave, lane, failed):
    start = datetime(2026, month, 2 + wave * 7)
    end = start + timedelta(days=5)
    focal = (month, dc, wave, lane) == (9, 1, 1, 0)
    payer = 1 if focal else RAND.choice([i for i in range(1, 25) if i not in (1, 2)])
    name = ATLAS if focal else f"Workload {month:02}-{dc:02}-{wave + 1}-{lane + 1}"
    reservation = f.add("reservation", None, payer, timestamp(start - timedelta(days=3)),
                        timestamp(start), timestamp(end), "approved", None, 25)
    deployment = f.add("deployment", None, reservation, name, "Synthetic customer workload",
                       timestamp(start), timestamp(end), "internal", "completed",
                       1 if focal else 2, "fixed")
    kinds = [1, 2] if lane == 0 or (dc + wave + month) % 3 else [1]
    if (dc + wave + lane) % 2 == 0:
        kinds.append(3)

    for kind in kinds:
        second_compute = kind == 1 and lane == 0 and (focal or failed or wave == 0)
        dimensions = {1: (8, 32, 0, 0), 2: (0, 0, 1500, 0), 3: (0, 0, 0, 10)}[kind]
        item = f.add("reservation_item", None, reservation, kind, 2 if second_compute else 1,
                     *dimensions, None, None, dc, "mandatory")
        subscription = f.add("deployment_service", None, deployment, kind, timestamp(start), timestamp(end))

        def assign(slot, begin, stop, predecessor=None):
            return f.add("resource_allocation", None, deployment, item, resource_id(dc, kind, slot),
                         0.5, timestamp(begin), timestamp(stop), "assigned", predecessor,
                         "Hardware failure" if predecessor else "Initial assignment", 25)

        slot = (0 if lane == 0 else 1 if wave == 0 and not failed else 2) if kind == 1 else lane
        breaks = kind == 1 and lane == 0 and failed
        if breaks:
            allocation = assign(slot, start, start + timedelta(days=1))
            replacement = assign(3, start + timedelta(days=2), end, allocation)
        else:
            allocation = assign(slot, start, end)
        if second_compute:
            assign(1, start, end)

        split = focal or (payer in (17, 18) and wave in (1, 3))
        draft = month == 10 or (dc == 9 and wave == 3)
        for offset in range(5):
            if breaks and offset == 1:
                continue
            day = start + timedelta(days=offset)
            estimate = RAND.randint(65, 140) if kind == 1 else RAND.randint(180, 420)
            quantity = round(estimate * RAND.uniform(0.80, 1.24 if kind == 1 else 1.12))
            reference_usage = focal and kind == 1 and offset == 2
            if reference_usage:
                estimate, quantity = 100, 120
            elif (dc + month + lane + offset + kind) % 17 == 0:
                estimate = None
            charge, amount = add_usage(
                f, subscription, replacement if breaks and offset >= 2 else allocation,
                kind, day, quantity, estimate, corrected=reference_usage,
                pending_meter=(month, dc, wave, lane, kind, offset) == (10, 4, 3, 0, 1, 0),
            )
            if charge is None:
                continue
            # Draft exceptions demonstrate both underallocation and absent allocation.
            if (month, dc, wave, lane, kind, offset) == (10, 3, 2, 1, 1, 0):
                f.shares(charge, amount - 100, payer, month, True, False)
            elif (month, dc, wave, lane, kind, offset) != (10, 7, 2, 1, 1, 0):
                f.shares(charge, amount, payer, month, draft, split)
            if reference_usage:
                credit = f.add("charge", None, None, None, None, charge, 26, "credit", -600,
                               "posted", "Outage service credit", timestamp(end + timedelta(days=1)))
                f.shares(credit, -600, payer, month, draft, split)
        if kind == 1 and (focal or (dc + month + wave) % 7 == 0):
            fee = f.add("charge", None, None, subscription, None, None, None, "direct", 750,
                        "posted", "Deployment setup fee", timestamp(start))
            f.shares(fee, 750, payer, month, draft, split)


def main():
    f = Fixture()
    reference_data(f)
    outages = incidents(f)
    for month in range(5, 11):
        for wave in range(4):
            for dc in range(1, 10):
                for lane in range(2):
                    work(f, month, dc, wave, lane, (month, dc, wave) in outages)
        # Pending and rejected requests provide controls for fulfillment queries.
        for client, status in ((1, "pending"), (2, "rejected")):
            start_at = timestamp(datetime(2026, month, 5))
            end_at = timestamp(datetime(2026, month, 8))
            request = f.add("reservation", None, client, START, start_at, end_at, status, None, None)
            f.add("reservation_item", None, request, 1, 1, 8, 32, 0, 0, 1, None, None, "preferred")
    for (_, month, draft), invoice in f.invoices.items():
        if not draft:
            assert f.invoice_balances[invoice] > 0
            issued = timestamp(datetime(2026, month + 1, 2))
            f.run("UPDATE invoice SET issuedAt = ?, status = 'issued' WHERE invoiceId = ?", issued, invoice)
    f.db.commit()
    assert not f.db.execute("PRAGMA foreign_key_check").fetchall()
    (SQL / "02_seed.sql").write_text(
        "-- Generated by scripts/seed_milestone2.py. Apply once to the empty schema.\n"
        "PRAGMA foreign_keys = ON;\nBEGIN;\n" +
        "\n".join(f.dml) + "\nCOMMIT;\n"
    )


if __name__ == "__main__":
    main()
