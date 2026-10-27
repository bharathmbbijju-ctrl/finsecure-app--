import streamlit as st
from datetime import date
import db

ADMIN_USERNAME = "your_username_here"

st.set_page_config(page_title="FinSecure", page_icon="🔐", layout="wide")
db.init_db()

if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None


# ---------------- LOGIN / REGISTER PAGE ----------------
def login_page():
    st.title("🔐 FinSecure")
    st.caption("Safe Digital Finance Manager")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        u = st.text_input("Username", key="login_user").strip()
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            uid = db.verify_user(u, p)
            if uid:
                db.record_login(uid)
                st.session_state.user_id = uid
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Wrong username or password")

    with tab_register:
        u = st.text_input("Choose a username", key="reg_user").strip()
        p = st.text_input("Choose a password (min 6 characters)",
                          type="password", key="reg_pass")
        if st.button("Create account"):
            if len(u) < 3 or len(p) < 6:
                st.warning("Username needs 3+ characters and password 6+.")
            elif db.create_user(u, p):
                st.success("Account created! Go to the Login tab.")
            else:
                st.error("That username is already taken.")


# ---------------- HELPER: DELETE BOX ----------------
def delete_box(table, df, key):
    if df.empty:
        return
    st.write("**Delete a record**")
    rid = st.selectbox("Select ID", df["id"], key=key)
    if st.button("Delete", key=key + "_btn"):
        db.delete_record(table, int(rid), st.session_state.user_id)
        st.rerun()


# ---------------- MAIN APP ----------------
def main_page():
    uid = st.session_state.user_id

    st.sidebar.write(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

    st.title("🔐 FinSecure")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Dashboard", "💸 Income & Expenses", "🏠 Assets", "🏦 Loans"]
    )

    # ----- Income & Expenses -----
    with tab2:
        st.subheader("Add a transaction")
        with st.form("txn_form", clear_on_submit=True):
            kind = st.radio("Type", ["Income", "Expense"], horizontal=True)
            category = st.selectbox(
                "Category",
                ["Salary", "Food", "Rent", "Travel", "Shopping",
                 "Bills", "Education", "Health", "Other"],
            )
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
            note = st.text_input("Note (optional)")
            d = st.date_input("Date", value=date.today())
            if st.form_submit_button("Add"):
                if amount > 0:
                    db.add_transaction(uid, kind, category, amount, note, str(d))
                    st.success("Added!")
                else:
                    st.warning("Amount must be more than 0.")

        txns = db.get_transactions(uid)
        st.subheader("All transactions")
        st.dataframe(txns)
        delete_box("transactions", txns, "del_txn")

    # ----- Assets -----
    with tab3:
        st.subheader("Add an asset")
        with st.form("asset_form", clear_on_submit=True):
            name = st.text_input("Asset name (e.g. Savings, Gold, Laptop)")
            value = st.number_input("Value (₹)", min_value=0.0, step=1000.0)
            if st.form_submit_button("Add asset"):
                if name and value > 0:
                    db.add_asset(uid, name, value)
                    st.success("Asset added!")
                else:
                    st.warning("Enter a name and a value above 0.")

        assets = db.get_assets(uid)
        st.dataframe(assets)
        delete_box("assets", assets, "del_asset")

    # ----- Loans -----
    with tab4:
        st.subheader("Add a loan")
        with st.form("loan_form", clear_on_submit=True):
            name = st.text_input("Loan name (e.g. Education loan)")
            amount = st.number_input("Amount owed (₹)", min_value=0.0, step=1000.0)
            rate = st.number_input("Interest rate (% per year)",
                                   min_value=0.0, step=0.5)
            if st.form_submit_button("Add loan"):
                if name and amount > 0:
                    db.add_loan(uid, name, amount, rate)
                    st.success("Loan added!")
                else:
                    st.warning("Enter a name and an amount above 0.")

        loans = db.get_loans(uid)
        st.dataframe(loans)
        delete_box("loans", loans, "del_loan")

    # ----- Dashboard -----
    with tab1:
        txns = db.get_transactions(uid)
        assets = db.get_assets(uid)
        loans = db.get_loans(uid)

        income = txns.loc[txns["kind"] == "Income", "amount"].sum()
        expense = txns.loc[txns["kind"] == "Expense", "amount"].sum()
        total_assets = assets["value"].sum()
        total_loans = loans["amount"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"₹{income:,.0f}")
        c2.metric("Total Expenses", f"₹{expense:,.0f}")
        c3.metric("Savings", f"₹{income - expense:,.0f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Total Assets", f"₹{total_assets:,.0f}")
        c5.metric("Total Loans", f"₹{total_loans:,.0f}")
        c6.metric("Net Worth", f"₹{total_assets - total_loans:,.0f}")

        st.subheader("Expenses by category")
        exp = txns[txns["kind"] == "Expense"]
        if exp.empty:
            st.info("No expenses yet. Add some in the Income & Expenses tab.")
        else:
            st.bar_chart(exp.groupby("category")["amount"].sum())

    # ----- Admin stats (only visible to the admin account) -----
    if st.session_state.username == ADMIN_USERNAME:
        st.divider()
        st.subheader("🛠 Admin: Usage stats")
        total_users, total_logins, logins_today, users_today, recent = (
            db.get_login_stats()
        )
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Registered users", total_users)
        a2.metric("Total logins", total_logins)
        a3.metric("Logins today", logins_today)
        a4.metric("Unique users today", users_today)
        st.write("**Last 20 logins**")
        st.dataframe(recent)


# ---------------- ROUTER ----------------
if st.session_state.user_id is None:
    login_page()
else:
    main_page()
