import streamlit as st
import pandas as pd
import numpy as np

from data_handler import load_prices, calculate_daily_returns, calculate_cumulative_returns
from optimizer import optimize_portfolio
from visualizations import plot_pie_chart, plot_cumulative_returns

# -----------------------------
# Define preloaded portfolios
# -----------------------------
PRELOADED_PORTFOLIOS = {
    "Tech Core": {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "AMZN": 0.25},
    "Dividend Mix": {"JNJ": 0.2, "PG": 0.2, "KO": 0.2, "PEP": 0.2, "MCD": 0.2},
    "Global ETF Blend": {"SPY": 0.4, "EFA": 0.3, "EEM": 0.2, "AGG": 0.1},
}

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Portfolio Optimizer", layout="wide")
st.title("📈 Portfolio Optimization Web App")

# Sidebar - Input Mode
st.sidebar.header("Portfolio Input")
input_mode = st.sidebar.radio("Choose input mode:", ( "Manual Entry", "Preloaded Portfolio"))

# Load portfolio
portfolio = {}
try:
    if input_mode == "Manual Entry":
        st.sidebar.subheader("Manual Portfolio Entry")
        tickers = st.sidebar.text_area("Enter tickers separated by commas", "AAPL,MSFT,GOOGL")
        weights = st.sidebar.text_area("Enter weights separated by commas", "0.3,0.4,0.3")

        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        weight_list = [float(w.strip()) for w in weights.split(",")]
        assert sum(weight_list) == 1.0, "Sum of weights should be 1"
        if len(ticker_list) == len(weight_list):
            portfolio = dict(zip(ticker_list, weight_list))
        else:
            raise Exception("Number of tickers and weights must match.")
    

    elif input_mode == "Preloaded Portfolio":
        selected = st.sidebar.selectbox("Choose a portfolio:", list(PRELOADED_PORTFOLIOS.keys()))
        portfolio = PRELOADED_PORTFOLIOS[selected]
except Exception as e:
    st.sidebar.error(f"{str(e)}")
    
try:
# Button to trigger optimization
    if st.sidebar.button("Optimize Portfolio"):
        if not portfolio:
            st.error("Please provide a valid portfolio.")
        else:
            tickers = list(portfolio.keys())
            weights = list(portfolio.values())

            with st.spinner("Fetching price data..."):
                prices = load_prices(tickers)
                daily_returns = calculate_daily_returns(prices)
                cumulative_return = calculate_cumulative_returns(daily_returns)

                benchamrk_prices = load_prices(["^GSPC"])
                benchamrk_daily_returns = calculate_daily_returns(benchamrk_prices)
                benchamrk_cumulative_return = calculate_cumulative_returns(benchamrk_daily_returns)

            with st.spinner("Optimizing portfolio..."):
                original_allocation_return = np.mean((daily_returns * weights).sum(axis=1)) * 252
                original_allocation_vol = np.std((daily_returns * weights).sum(axis=1)) * np.sqrt(252)
                original_allocation_sharpe = original_allocation_return / original_allocation_vol
                benchmark_return = np.mean(benchamrk_daily_returns) * 252
                benchmark_vol = (np.std(benchamrk_daily_returns) * np.sqrt(252)).iat[0]
                benchmark_sharpe = benchmark_return / benchmark_vol

                results = {"Original": {"weights": weights, 
                                        "metrics": {
                                            "Annual Return": original_allocation_return,
                                            "Volatility": original_allocation_vol,
                                            "Sharpe Ratio": original_allocation_sharpe
                                            }
                                        },
                            "S&P 500": {"metrics": {
                                            "Annual Return": benchmark_return,
                                            "Volatility": benchmark_vol,
                                            "Sharpe Ratio": benchmark_sharpe
                                            }
                                        }
                            }
                methods = {"Original": weights, "Max Sharpe": None, "Min Volatility": None}

                for name, method in [("Max Sharpe", "sharpe"), ("Min Volatility", "min_vol")]:
                    res = optimize_portfolio(daily_returns, method=method)
                    methods[name] = list(res["Optimal Weights"].values())
                    results[name] = {
                        "weights": res["Optimal Weights"],
                        "metrics": {
                            "Annual Return": res["Annual Return"],
                            "Volatility": res["Volatility"],
                            "Sharpe Ratio": res["Sharpe Ratio"]
                        }
                    }

            st.success("Optimization Complete!")

            # 📈 Performance Chart
            st.subheader("📈 Portfolio Performance")
            cumulative_returns_df = pd.DataFrame()
            for label, w in methods.items():
                ptf_returns = (daily_returns * w).sum(axis=1)
                cumulative_returns_df[label] = calculate_cumulative_returns(ptf_returns)
            cumulative_returns_df["S&P 500"] = calculate_cumulative_returns(benchamrk_daily_returns)
            st.plotly_chart(plot_cumulative_returns(cumulative_returns_df))

            # 📋 Metrics Table
            st.subheader("🧠 Risk & Return Metrics")

            def format_metrics(metrics):
                return {
                    "Annual Return": f"{metrics['Annual Return'] * 100:.2f}%",
                    "Volatility": f"{metrics['Volatility'] * 100:.2f}%",
                    "Sharpe Ratio": f"{metrics['Sharpe Ratio']:.2f}"
                }

            metrics_table = {
                label: format_metrics({
                    "Annual Return": results.get(label, {}).get("metrics", {}).get("Annual Return", 0),
                    "Volatility": results.get(label, {}).get("metrics", {}).get("Volatility", 0) ,
                    "Sharpe Ratio": results.get(label, {}).get("metrics", {}).get("Sharpe Ratio", 0)
            }) for label in results.keys()}

            metrics_df = pd.DataFrame(metrics_table).T.reset_index().rename(columns={"index": "Portfolio"})
            metrics_df.set_index("Portfolio", inplace=True)
            st.write(metrics_df)

            # 📊 Portfolio Allocation Tabs
            st.subheader("📊 Portfolio Allocations")
            tab1, tab2, tab3 = st.tabs(["Original", "Max Sharpe", "Min Volatility"])

            with tab1:
                st.plotly_chart(plot_pie_chart(portfolio, title="Original Portfolio Allocation"))

            with tab2:
                st.plotly_chart(plot_pie_chart(results["Max Sharpe"]["weights"], title="Max Sharpe Allocation"))

            with tab3:
                st.plotly_chart(plot_pie_chart(results["Min Volatility"]["weights"], title="Min Volatility Allocation"))


    else:
        st.info("⬅️ Upload your portfolio or select a sample on the sidebar to start optimizing.")
except Exception as e:
    st.sidebar.error(f"{str(e)}")