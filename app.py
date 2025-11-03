import streamlit as st
import pandas as pd


# ---- Civic Metrics ----
def compute_metrics(df, fairness_method="difference"):
    df['budget'] = df['budget'].astype(float)
    df['population'] = df['population'].astype(float)
    total_budget = df['budget'].sum()
    total_population = df['population'].sum()
    df['budget_share'] = df['budget'] / total_budget * 100
    df['population_share'] = df['population'] / total_population * 100
    
    # Different fairness calculation methods
    if fairness_method == "difference":
        # Simple difference
        df['fairness_index'] = df['budget_share'] - df['population_share']
    elif fairness_method == "proportional":
        # Proportional deviation (1 - |difference| / population_share)
        df['fairness_index'] = 1 - (abs(df['budget_share'] - df['population_share']) / df['population_share'])
        df['fairness_index'] = df['fairness_index'].clip(lower=0.0, upper=1.0) * 100  # Scale to percentage
    elif fairness_method == "ratio":
        # Ratio-based (1 = perfect fairness)
        df['fairness_index'] = (df['budget_share'] / df['population_share'] - 1) * 100
    
    df['fairness_ratio'] = df['budget_share'] / df['population_share']
    return df


# ---- Charts ----
def render_chart(df):
    chart_data = df.set_index('sector')[['budget_share', 'population_share']]
    st.bar_chart(chart_data)


def render_table(df):
    st.subheader("Civic Data Table")
    if hasattr(st, 'data_editor'):
        return st.data_editor(df, num_rows="dynamic")
    else:
        st.dataframe(df)
        return df


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
    
    # Explanation based on method
    if fairness_method == "difference":
        st.write("**Method:** Simple Difference (Budget Share % - Population Share %)")
        st.write("• Positive = over-funded | Negative = under-funded | Zero = perfectly fair")
    elif fairness_method == "proportional":
        st.write("**Method:** Proportional Deviation (1 - |difference| / population_share)")
        st.write("• 100% = perfectly fair | Lower % = less fair | Scale: 0-100%")
    elif fairness_method == "ratio":
        st.write("**Method:** Ratio-based ((Budget Share / Population Share) - 1) × 100")
        st.write("• 0% = perfectly fair | Positive = over-funded | Negative = under-funded")
    
    show_cols = ['sector', 'budget', 'population', 'budget_share', 'population_share', 'fairness_index', 'fairness_ratio']
    df_display = df[show_cols].copy()
    df_display.columns = [
        "Sector", "Budget", "Population", "Budget Share (%)", "Population Share (%)",
        "Fairness Index", "Fairness Ratio"
    ]
    
    # Format based on method
    format_dict = {
        "Budget Share (%)": "{:.2f}",
        "Population Share (%)": "{:.2f}",
        "Fairness Ratio": "{:.2f}"
    }
    
    if fairness_method == "proportional":
        format_dict["Fairness Index"] = "{:.2f}%"
    else:
        format_dict["Fairness Index"] = "{:.2f}%"
    
    st.dataframe(df_display.style.format(format_dict))


def render_storytelling(df, fairness_method):
    st.subheader("AI Storytelling")
    
    if fairness_method == "proportional":
        # For proportional, lower is worse
        worst_idx = df['fairness_index'].idxmin()
        sector = df.loc[worst_idx, 'sector']
        fairness = df.loc[worst_idx, 'fairness_index']
        st.write(f"📉 The budget for **{sector}** shows the lowest fairness ({fairness:.1f}%), indicating the largest proportional mismatch.")
    else:
        # For difference and ratio, largest absolute deviation
        largest_gap = df['fairness_index'].abs().idxmax()
        sector = df.loc[largest_gap, 'sector']
        delta = df.loc[largest_gap, 'fairness_index']
        if delta < 0:
            st.write(f"📉 The budget for **{sector}** appears under-funded (deviation: {delta:.2f}%).")
        else:
            st.write(f"📈 The budget for **{sector}** appears over-funded (deviation: +{delta:.2f}%).")


# ---- Main ----
def main():
    st.title("Data4Civic")
    st.caption("Civic Data Transparency Dashboard")

    # Fairness Method Selection
    st.sidebar.header("Fairness Calculation Settings")
    fairness_method = st.sidebar.selectbox(
        "Select Fairness Index Method:",
        ["difference", "proportional", "ratio"],
        format_func=lambda x: {
            "difference": "Simple Difference (Budget - Population)",
            "proportional": "Proportional Deviation (Research Standard)",
            "ratio": "Ratio-based Analysis"
        }[x]
    )
    
    # Method description in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Method Explanation")
    if fairness_method == "difference":
        st.sidebar.info("**Simple Difference:** Budget Share % minus Population Share %. Positive means over-funded, negative means under-funded.")
    elif fairness_method == "proportional":
        st.sidebar.info("**Proportional (Standard):** 1 - |difference| / population_share. Used in academic research. 100% = perfectly fair.")
    elif fairness_method == "ratio":
        st.sidebar.info("**Ratio-based:** (Budget/Population ratio - 1) × 100. Shows percentage deviation from perfect proportionality.")

    uploaded_file = st.file_uploader("Upload your civic data CSV", type=['csv'])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if not {'sector','budget','population'}.issubset(df.columns):
                st.error("CSV must have columns: sector, budget, population")
                return
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return
    else:
        st.info("Upload a CSV file with columns: sector, budget, population")
        return

    df = compute_metrics(df, fairness_method)
    render_chart(df)
    df_edit = render_table(df)
    df_edit = compute_metrics(df_edit, fairness_method)
    render_fairness_index(df_edit, fairness_method)
    render_fairness_table(df_edit, fairness_method)
    render_storytelling(df_edit, fairness_method)


if __name__ == "__main__":
    main()
    
