"""Interactive QARM II demonstration on synthetic data."""
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
REPO_SRC = HERE.parent.parent / "src"
if REPO_SRC.is_dir():
    sys.path.insert(0, str(REPO_SRC))
sys.path.insert(0, str(HERE))

from model import ASSETS, calculate, holdout, metrics

st.set_page_config(page_title="RiskMatch · Projet QARM II", page_icon="◈", layout="wide")
st.markdown(
    """<style>
    .stApp { background: #f6f8f5; }
    [data-testid="stSidebar"] { background: #edf3ef; }
    [data-testid="stMetric"] { padding: 1rem; background: white; border: 1px solid #dce8df; border-radius: .55rem; }
    </style>""",
    unsafe_allow_html=True,
)
st.title("RiskMatch · Un portefeuille sous contraintes")
st.markdown(
    "Un client fictif investit **100 000 USD** et veut faire croître son capital "
    "tout en limitant la perte dans les chocs définis. Compare deux mandats "
    "pour voir ce que change réellement leur plafond de perte."
)
st.caption("Projet QARM II · Simulation sur données synthétiques · Portefeuille acheteur sans levier.")

with st.sidebar:
    st.header("Mandats à comparer")
    limit_a = st.slider("Perte maximale en stress · mandat A (%)", 3, 35, 20)
    limit_b = st.slider("Perte maximale en stress · mandat B (%)", 3, 35, 10)
    aversion = st.slider("Pénalisation de la variance", 1, 20, 5,
                         help="Une valeur plus élevée donne plus de poids à la variance dans l’objectif.")
    cap = st.slider("Poids maximal par actif (%)", 20, 100, 65)
    investable = st.multiselect("Actifs autorisés dans les deux mandats", ASSETS, default=list(ASSETS))

a = calculate(limit_a / 100, aversion, cap / 100, [name in investable for name in ASSETS])
b = calculate(limit_b / 100, aversion, cap / 100, [name in investable for name in ASSETS])

if a is None or b is None:
    st.warning("Au moins un mandat est infaisable avec cette combinaison d’actifs et de plafonds. "
               "Élargis les actifs admissibles ou ajuste les limites pour pouvoir investir 100 %.")
    st.stop()

ma = metrics(a["utility"], a["means"], a["covariance"])
mb = metrics(b["utility"], b["means"], b["covariance"])
comparison, research, allocation = st.tabs(["Comparer les mandats", "Méthode et test", "Composer le portefeuille"])

def percentage(x):
    return f"{x:.1%}".replace(".", ",")


with comparison:
    st.subheader("Effet du plafond de perte sur les poids")
    left, right = st.columns(2)
    left.metric("Perte au pire des chocs · A", percentage(ma["loss"]))
    right.metric("Perte au pire des chocs · B", percentage(mb["loss"]))
    weights = pd.DataFrame({"Mandat A": 100 * a["utility"], "Mandat B": 100 * b["utility"]}, index=ASSETS)
    st.bar_chart(weights, color=["#14796f", "#b96348"])
    st.table(weights.round(2).rename_axis("Poids (%)"))
    st.caption(
        f"Volatilité estimée A : {percentage(ma['volatility'])} · "
        f"B : {percentage(mb['volatility'])}. "
        f"Rendement annualisé estimé A : {percentage(ma['return'])} · B : {percentage(mb['return'])}."
    )
    change = 100 * (b["utility"][0] - a["utility"][0])
    st.write(f"Poids des actions US : {percentage(a['utility'][0])} dans A, "
             f"{percentage(b['utility'][0])} dans B ({change:+.1f} points).")
    st.subheader("Résultat par choc")
    st.table(pd.DataFrame({"Mandat A": {k: percentage(v) for k, v in ma["shocks"].items()},
                           "Mandat B": {k: percentage(v) for k, v in mb["shocks"].items()}}))

with research:
    st.subheader("Markowitz avec des limites de perte explicites")
    st.latex(r"max_wquad mu^mathsf{T}w-rac{lambda}{2}w^mathsf{T}Sigma w")
    st.latex(r"sum_i w_i=1,quad 0le w_ile u_i,quad s_j^mathsf{T}wge -Lquadorall j")
    st.markdown(
        "Les **96 premiers mois** déterminent les moyennes μ et la covariance Σ. "
        "Le plafond par ligne est u et λ pénalise la variance. Dans chaque choc j, "
        "le rendement du portefeuille est le produit scalaire des poids et du vecteur de chocs s. "
        "La limite L impose une perte maximale dans ces scénarios précis."
    )
    st.subheader("Test sur 24 mois gardés à part")
    st.line_chart(pd.DataFrame({"Mandat A": 100 * holdout(a["utility"]),
                                "Mandat B": 100 * holdout(b["utility"])}),
                  color=["#14796f", "#b96348"], x_label="Mois", y_label="Capital, base 100")
    st.caption("Les cibles sont calculées avant les 24 mois de test. "
               "Les titres sont conservés pendant le test, avec des frais d’entrée de 0,10 % sur le montant investi hors liquidités.")

with allocation:
    st.subheader("Combiner deux stratégies compatibles avec le mandat B")
    st.write("Combine l’allocation rendement-risque avec une référence de variance minimale. "
             "Les deux utilisent les mêmes limites de position et de stress.")
    share = st.slider("Part rendement-risque (%)", 0, 100, 75) / 100
    combined = share * b["utility"] + (1 - share) * b["defensive"]
    result = metrics(combined, b["means"], b["covariance"])
    st.metric("Perte au pire des chocs du mélange", percentage(result["loss"]))
    positions = pd.DataFrame({"Poids (%)": (100 * combined).round(2),
                              "Montant simulé (USD)": (100_000 * combined).round(2)},
                             index=pd.Index(ASSETS, name="Actif"))
    st.table(positions)
    st.caption("Le montage additionne les poids des titres présents dans les deux stratégies. "
               "Il conserve les contraintes linéaires communes.")
    reference = (limit_b, aversion, cap, tuple(investable), share)
    if st.button("Confirmer cette allocation simulée", type="primary"):
        st.session_state.confirmed_allocation = reference
    if st.session_state.get("confirmed_allocation") == reference:
        st.success("Allocation simulée confirmée pour le mandat B.")
