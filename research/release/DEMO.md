# RiskMatch · Fictional CHF household

Unzip the complete archive into a new directory. The application uses project-authored quotes and cash flows and runs on your computer. You need Python 3.12 and the OpenSSL command-line program. In the extracted directory run:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-app.txt
python -m streamlit run app/intake.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Open the local address printed by Streamlit. Select **Load fictional course mandate**, review the four screens and open the risk interview. Finish the interview, choose **Compare fictional portfolios** and select a mix. Consent to local storage to open the monitor. Increase the bill, compare holding and trading, and confirm the simulated change. Advance the feed until the stale-FX message appears.

The payment is CHF 15,000 out of CHF 50,000. The portable allocations and market updates are fictional. The numerical examples in the course slides have separate historical sources. Installation needs access to Python packages unless you have them cached. Once installed, the local demo runs offline. The included demo-requirements.lock records the tested macOS Python 3.12.6 environment.

The local account is accessible with its recovery key. Keep that key private. The monitor's delete action removes the stored account and its history. Use fictional inputs for the walkthrough. No money is transferred.
