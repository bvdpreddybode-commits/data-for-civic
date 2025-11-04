import streamlit as st
import pandas as pd

# ---- Civic Metrics ----
def compute_metrics(df, fairness_method="difference"):
    df = df.copy()

    # Ensure numeric types
    df['budget'] = pd.to_numeric(df['budget'], errors='coerce').fillna(0)
    df['population'] = pd.to_numeric(df['population'], errors='coerce').fillna(0)

    total_budget = df['budget'].sum()
    total_population = df['population'].sum()

    # Avoid division by zero
    if total_budget == 0 or total_population == 0:
        df['budget_share'] = 0
        df['population_share'] = 0
        df['fairness_index'] = 0
        df['fairness_ratio'] = 0
        return df

    # Calculate shares
    df['budget_share'] = (df['budget'] / total_budget) * 100
    df['population_share'] = (df['population'] / total_population) * 100

    # ---- Fairness Methods ----
    if fairness_method == "difference":
        df['fairness_index'] = df['budget_share'] - df['population_share']

    elif fairness_method == "proportional":
        df['fairness_index'] = 1 - (abs(df['budget_share'] - df['population_share']) / df['population_share'].replace(0, 1))
        df['fairness_index'] = df['fairness_index'].clip(0, 1) * 100  # Scale 0–100%

    elif fairness_method == "ratio":
        df['fairness_index'] = ((df['budget_share'] / df['population_share'].replace(0, 1)) - 1) * 100

    # Add Fairness Ratio (Budget/Population)
    df['fairness_ratio'] = df['budget_share'] / df['population_share'].replace(0, 1)

    return df


# ---- Charts ----
def render_chart(df):
    chart_data = df.set_index('sector')[['budget_share', 'population_share']]
    st.bar_chart(chart_data)


def render_table(df):
    st.subheader("Civic Data Table")
    if hasattr(st, 'data_editor'):
        df_edit = st.data_editor(df, num_rows="dynamic")
    else:
        st.dataframe(df)
        df_edit = df
    return df_edit


def render_fairness_index(df, fairness_method):
    avg_fairness = df['fairness_index'].mean()
    st.subheader("Overall Fairness Index")

    if fairness_method == "proportional":
        st.metric("Fairness Index (Average)", f"{avg_fairness:.2f}%")
        st.info("Higher percentage = more fair (100% = perfectly proportional)")
    else:
        st.metric("Fairness Index (Average)", f"{avg_fairness:.2f}%")
        if avg_fairness < 0:
            st.info("Negative values indicate under-funding relative to population share.")
        else:
            st.success("Positive values indicate over-funding relative to population share.")


def render_fairness_table(df, fairness_method):
    st.subheader("Fairness Calculator (Detail by Sector)")

    # Explanation
    explanations = {
        "difference": "**Method:** Simple Difference (Budget Share % - Population Share %)",
        "proportional": "**Method:** Proportional Deviation (1 - |difference| / population_share)",
        "ratio": "**Method:** Ratio-based ((Budget Share / Population Share) - 1) × 100"
    }
    st.write(explanations.get(fairness_method, ""))

    df_display = df[['sector', 'budget', 'population', 'budget_share',
                     'population_share', 'fairness_index', 'fairness_ratio']].copy()

    df_display.columns = [
        "Sector", "Budget", "Population", "Budget Share (%)",
        "Population Share (%)", "Fairness Index", "Fairness Ratio"
    ]

    format_dict = {
        "Budget Share (%)": "{:.2f}",
        "Population Share (%)": "{:.2f}",
        "Fairness Ratio": "{:.2f}",
        "Fairness Index": "{:.2f}"
    }

    st.dataframe(df_display.style.format(format_dict))


def render_storytelling(df, fairness_method):
    st.subheader("AI Storytelling")

    if fairness_method == "proportional":
        worst_idx = df['fairness_index'].idxmin()
        sector = df.loc[worst_idx, 'sector']
        fairness = df.loc[worst_idx, 'fairness_index']
        st.write(f"📉 **{sector}** shows the lowest fairness ({fairness:.1f}%), indicating the largest proportional mismatch.")
    else:
        largest_gap = df['fairness_index'].abs().idxmax()
        sector = df.loc[largest_gap, 'sector']
        delta = df.loc[largest_gap, 'fairness_index']
        if delta < 0:
            st.write(f"📉 **{sector}** appears under-funded (deviation: {delta:.2f}%).")
        else:
            st.write(f"📈 **{sector}** appears over-funded (deviation: +{delta:.2f}%).")


# ---- Main ----
def main():
    st.title("Data4Civic – Fairness Dashboard")
    st.caption("Analyze fairness between population share and budget allocation")

    st.sidebar.header("Fairness Calculation Settings")
    fairness_method = st.sidebar.selectbox(
        "Select Fairness Index Method:",
        ["difference", "proportional", "ratio"],
        format_func=lambda x: {
            "difference": "Simple Difference",
            "proportional": "Proportional Deviation",
            "ratio": "Ratio-based"
        }[x]
    )

    st.sidebar.markdown("---")

    uploaded_file = st.file_uploader("Upload CSV (columns: sector, budget, population)", type=['csv'])

    if uploaded_file is None:
        st.info("Upload a CSV file with columns: `sector`, `budget`, `population`")
        return

    try:
        df = pd.read_csv(uploaded_file)
        if not {'sector', 'budget', 'population'}.issubset(df.columns):
            st.error("CSV must include: sector, budget, population")
            return
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return

    # Compute and visualize
    df = compute_metrics(df, fairness_method)
    render_chart(df)
    df_edit = render_table(df)
    df_edit = compute_metrics(df_edit, fairness_method)
    render_fairness_index(df_edit, fairness_method)
    render_fairness_table(df_edit, fairness_method)
    render_storytelling(df_edit, fairness_method)


if __name__ == "__main__":
    main()
