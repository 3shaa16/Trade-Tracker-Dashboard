import streamlit as st
import plotly.express as px
import pandas as pd

from database import (
    create_tables,
    add_trade,
    get_all_trades,
    get_dashboard_stats,
    close_trade,
    delete_trade,
    save_profile,
    get_profile,
    update_trade
)

create_tables()

st.set_page_config(page_title="Trade Tracker", layout="wide")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Trade", "Trades", "Settings"]
)

if page == "Dashboard":
    st.title("Dashboard")

    profile = get_profile()
    stats = get_dashboard_stats()

    starting_balance = float(profile["starting_balance"]) if profile else 0.0
    currency = profile["currency"] if profile else "USD"

    df = get_all_trades()
    closed_df = df[df["status"] == "Closed"].copy()
    open_df = df[df["status"] == "Open"].copy()

    filter_option = st.selectbox(
        "Filter Dashboard",
        ["All Time", "Today", "This Week", "This Month", "Custom Range"]
    )

    if len(closed_df) > 0:
        closed_df["date"] = pd.to_datetime(closed_df["date"])
        closed_df["profit_loss"] = closed_df["profit_loss"].fillna(0)

        today = pd.Timestamp.today().normalize()

        if filter_option == "Today":
            closed_df = closed_df[closed_df["date"] == today]

        elif filter_option == "This Week":
            start_week = today - pd.Timedelta(days=today.weekday())
            closed_df = closed_df[closed_df["date"] >= start_week]

        elif filter_option == "This Month":
            closed_df = closed_df[
                (closed_df["date"].dt.month == today.month) &
                (closed_df["date"].dt.year == today.year)
            ]

        elif filter_option == "Custom Range":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")

            closed_df = closed_df[
                (closed_df["date"] >= pd.to_datetime(start_date)) &
                (closed_df["date"] <= pd.to_datetime(end_date))
            ]

    total_profit = closed_df["profit_loss"].fillna(0).sum() if len(closed_df) > 0 else 0
    current_capital = starting_balance + total_profit
    roi = (total_profit / starting_balance * 100) if starting_balance > 0 else 0

    open_exposure = open_df["entry_amount"].sum() if len(open_df) > 0 else 0

    filtered_closed = len(closed_df)
    filtered_wins = len(closed_df[closed_df["profit_loss"] > 0]) if len(closed_df) > 0 else 0

    filtered_win_rate = (
        filtered_wins / filtered_closed * 100
        if filtered_closed > 0
        else 0
    )

    profit_color = "green" if total_profit >= 0 else "red"

    st.markdown(
        f"""
        <div style="padding:20px;border-radius:15px;background-color:#111827;margin-bottom:20px;">
            <h3 style="color:white;">Portfolio Summary</h3>
            <h1 style="color:{profit_color};">{currency} {total_profit:.2f}</h1>
            <p style="color:#d1d5db;">Total Profit / Loss</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Starting Capital", f"{currency} {starting_balance:.2f}")
    c2.metric("Current Capital", f"{currency} {current_capital:.2f}")
    c3.metric("ROI", f"{roi:.2f}%")
    c4.metric("Open Exposure", f"{currency} {open_exposure:.2f}")

    c5, c6, c7, c8 = st.columns(4)

    c5.metric("Closed Trades", filtered_closed)
    c6.metric("Open Trades", stats["open"])
    c7.metric("Win Rate", f"{filtered_win_rate:.1f}%")
    c8.metric("Total Trades", len(df))

    if len(closed_df) == 0:
        st.info("No closed trades yet. Close a trade to see charts.")

    else:
        st.subheader("Profit/Loss by Trade")

        fig_trade = px.bar(
            closed_df,
            x="title",
            y="profit_loss",
            title="Individual Trade Profit/Loss",
            color="profit_loss",
            color_continuous_scale=["red", "green"]
        )
        st.plotly_chart(fig_trade, use_container_width=True)

        st.subheader("Daily Profit/Loss")

        daily_df = (
            closed_df
            .groupby("date")["profit_loss"]
            .sum()
            .reset_index()
        )

        fig_daily = px.line(
            daily_df,
            x="date",
            y="profit_loss",
            markers=True,
            title="Daily Profit/Loss"
        )
        st.plotly_chart(fig_daily, use_container_width=True)

        st.subheader("Equity Curve")

        equity_df = closed_df.sort_values("date").copy()
        equity_df["cumulative_profit"] = equity_df["profit_loss"].cumsum()
        equity_df["capital"] = starting_balance + equity_df["cumulative_profit"]

        fig_equity = px.line(
            equity_df,
            x="date",
            y="capital",
            markers=True,
            title="Capital Growth / Equity Curve"
        )
        st.plotly_chart(fig_equity, use_container_width=True)

        st.subheader("Weekly Profit/Loss")

        weekly_source = closed_df.copy()
        weekly_source["week"] = weekly_source["date"].dt.to_period("W").astype(str)

        weekly_df = (
            weekly_source
            .groupby("week")["profit_loss"]
            .sum()
            .reset_index()
        )

        fig_weekly = px.bar(
            weekly_df,
            x="week",
            y="profit_loss",
            title="Weekly Profit/Loss",
            color="profit_loss",
            color_continuous_scale=["red", "green"]
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

        st.subheader("Monthly Profit/Loss")

        monthly_source = closed_df.copy()
        monthly_source["month"] = monthly_source["date"].dt.to_period("M").astype(str)

        monthly_df = (
            monthly_source
            .groupby("month")["profit_loss"]
            .sum()
            .reset_index()
        )

        fig_monthly = px.bar(
            monthly_df,
            x="month",
            y="profit_loss",
            title="Monthly Profit/Loss",
            color="profit_loss",
            color_continuous_scale=["red", "green"]
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

elif page == "Add Trade":
    st.title("Add Trade")

    date = st.date_input("Trade Date")
    title = st.text_input("Title / Match / Asset")
    entry_amount = st.number_input("Entry Amount", min_value=0.0)

    status = st.selectbox("Trade Status", ["Open", "Closed"])

    exit_amount = None
    profit_loss = None

    if status == "Closed":
        exit_amount = st.number_input("Exit Amount", min_value=0.0)
        profit_loss = exit_amount - entry_amount

        if profit_loss >= 0:
            st.success(f"Profit: {profit_loss:.2f}")
        else:
            st.error(f"Loss: {profit_loss:.2f}")

    notes = st.text_area("Notes")
    link = st.text_input("Link")

    if st.button("Save Trade"):
        if title.strip() == "":
            st.error("Title is required.")
        else:
            add_trade(
                str(date),
                title,
                entry_amount,
                status,
                exit_amount,
                profit_loss,
                notes,
                link
            )
            st.success("Trade saved successfully!")

elif page == "Trades":
    st.title("Trades")

    df = get_all_trades()

    if len(df) == 0:
        st.info("No trades saved yet.")

    else:
        display_df = df[
            [
                "id",
                "date",
                "title",
                "entry_amount",
                "exit_amount",
                "profit_loss",
                "status",
                "notes",
                "link"
            ]
        ].copy()

        def color_profit_loss(value):
            if pd.isna(value):
                return ""
            if value > 0:
                return "color: green; font-weight: bold;"
            if value < 0:
                return "color: red; font-weight: bold;"
            return ""

        styled_df = display_df.style.map(
            color_profit_loss,
            subset=["profit_loss"]
        )

        st.dataframe(styled_df, use_container_width=True)

        st.subheader("Close Open Trade")

        open_trades = df[df["status"] == "Open"]

        if len(open_trades) == 0:
            st.info("No open trades.")
        else:
            trade_options = {
                f"{row['id']} - {row['title']} - Entry: {row['entry_amount']}": row["id"]
                for _, row in open_trades.iterrows()
            }

            selected_trade = st.selectbox(
                "Select trade to close",
                list(trade_options.keys())
            )

            exit_amount = st.number_input(
                "Exit Amount",
                min_value=0.0,
                key="close_exit_amount"
            )

            if st.button("Close Trade"):
                close_trade(trade_options[selected_trade], exit_amount)
                st.success("Trade closed successfully!")
                st.rerun()

        st.subheader("Edit Trade")

        trade_options_edit = {
            f"{row['id']} - {row['title']} - {row['status']}": row["id"]
            for _, row in df.iterrows()
        }

        selected_edit = st.selectbox(
            "Select trade to edit",
            list(trade_options_edit.keys())
        )

        selected_edit_id = trade_options_edit[selected_edit]
        selected_row = df[df["id"] == selected_edit_id].iloc[0]

        edit_date = st.date_input(
            "Edit Date",
            value=pd.to_datetime(selected_row["date"]).date(),
            key="edit_date"
        )

        edit_title = st.text_input(
            "Edit Title",
            value=selected_row["title"],
            key="edit_title"
        )

        edit_entry = st.number_input(
            "Edit Entry Amount",
            min_value=0.0,
            value=float(selected_row["entry_amount"]),
            key="edit_entry"
        )

        edit_status = st.selectbox(
            "Edit Status",
            ["Open", "Closed"],
            index=0 if selected_row["status"] == "Open" else 1,
            key="edit_status"
        )

        edit_exit = None

        if edit_status == "Closed":
            default_exit = (
                float(selected_row["exit_amount"])
                if pd.notna(selected_row["exit_amount"])
                else 0.0
            )

            edit_exit = st.number_input(
                "Edit Exit Amount",
                min_value=0.0,
                value=default_exit,
                key="edit_exit"
            )

            edit_profit_loss = edit_exit - edit_entry

            if edit_profit_loss >= 0:
                st.success(f"Updated Profit: {edit_profit_loss:.2f}")
            else:
                st.error(f"Updated Loss: {edit_profit_loss:.2f}")

        edit_notes = st.text_area(
            "Edit Notes",
            value=selected_row["notes"] if pd.notna(selected_row["notes"]) else "",
            key="edit_notes"
        )

        edit_link = st.text_input(
            "Edit Link",
            value=selected_row["link"] if pd.notna(selected_row["link"]) else "",
            key="edit_link"
        )

        if st.button("Update Trade"):
            update_trade(
                selected_edit_id,
                str(edit_date),
                edit_title,
                edit_entry,
                edit_status,
                edit_exit,
                edit_notes,
                edit_link
            )
            st.success("Trade updated successfully!")
            st.rerun()

        st.subheader("Delete Trade")

        trade_options_delete = {
            f"{row['id']} - {row['title']} - {row['status']}": row["id"]
            for _, row in df.iterrows()
        }

        selected_delete = st.selectbox(
            "Select trade to delete",
            list(trade_options_delete.keys())
        )

        if st.button("Delete Trade"):
            delete_trade(trade_options_delete[selected_delete])
            st.success("Trade deleted successfully!")
            st.rerun()

elif page == "Settings":
    st.title("Settings")

    profile = get_profile()

    default_name = profile["name"] if profile else ""
    default_balance = float(profile["starting_balance"]) if profile else 0.0
    default_currency = profile["currency"] if profile else "USD"

    name = st.text_input("Profile Name", value=default_name)

    starting_balance = st.number_input(
        "Starting Capital",
        min_value=0.0,
        value=default_balance
    )

    currencies = ["USD", "INR", "EUR", "GBP"]

    currency = st.selectbox(
        "Currency",
        currencies,
        index=currencies.index(default_currency)
        if default_currency in currencies
        else 0
    )

    if st.button("Save Settings"):
        save_profile(name, starting_balance, currency)
        st.success("Settings saved!")
        st.rerun()