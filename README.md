# CDA Generator

Turns a RealtyOne Plus **DATA WORKSHEET** Excel file into a Commission Disbursement Authorization PDF.

The worksheet layout is the ROP sale/lease sheet (property, parties, title, and commission rows). Brokerage letterhead, broker name, and agent payee mailing addresses live in `config/defaults.json` because those values are not on the worksheet.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000), upload a `.xlsx` worksheet, review the parsed fields, and download the PDF.

An example worksheet and the original Word CDA are in `examples/`.

## Customize

Edit `config/defaults.json` to set:

- Broker name (signature line)
- Brokerage mailing address, email, and phone
- Selling-agent payee addresses keyed by agent name
