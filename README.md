# Amazon Category Dashboard

Interactive Streamlit dashboard for Amazon product ratings, prices, discounts, and category-level metrics.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app loads `amazon.csv` from this directory automatically. It falls back to a CSV upload if the bundled file is unavailable.
