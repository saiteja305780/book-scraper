import pandas as pd
import streamlit as st

st.set_page_config(page_title="Books Dashboard", page_icon="📚", layout="wide")

CSV_PATH = "books.csv"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df.dropna(subset=["price", "rating"]).astype({"rating": int})


try:
    df = load_data(CSV_PATH)
except FileNotFoundError:
    st.error(f"Couldn't find '{CSV_PATH}'. Run books_scraper.py first and keep the CSV in this folder.")
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")

price_min, price_max = float(df["price"].min()), float(df["price"].max())
price_range = st.sidebar.slider("Price (£)", price_min, price_max, (price_min, price_max))

ratings = st.sidebar.multiselect(
    "Rating (stars)", options=[1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5]
)

search = st.sidebar.text_input("Search title")

filtered = df[
    df["price"].between(*price_range)
    & df["rating"].isin(ratings)
    & df["title"].str.contains(search, case=False, na=False)
]

# ---------- Header + KPIs ----------
st.title("📚 Books Scraping Dashboard")
st.caption("Data scraped from books.toscrape.com with requests + BeautifulSoup")

if filtered.empty:
    st.warning("No books match the current filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Books", f"{len(filtered):,}")
c2.metric("Average price", f"£{filtered['price'].mean():.2f}")
c3.metric("Average rating", f"{filtered['rating'].mean():.2f} ★")
c4.metric("4-5 star books", f"{(filtered['rating'] >= 4).mean() * 100:.0f}%")

st.divider()

# ---------- Charts ----------
left, right = st.columns(2)

with left:
    st.subheader("Books by rating")
    rating_counts = filtered["rating"].value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    rating_counts.index = [f"{i} ★" for i in rating_counts.index]
    st.bar_chart(rating_counts)

with right:
    st.subheader("Price distribution")
    bins = list(range(0, 70, 10))
    labels = [f"£{a}-{b}" for a, b in zip(bins[:-1], bins[1:])]
    price_bins = pd.cut(filtered["price"], bins=bins, labels=labels, right=False)
    st.bar_chart(price_bins.value_counts(sort=False))

left2, right2 = st.columns(2)

with left2:
    st.subheader("Average price by rating")
    avg_price = filtered.groupby("rating")["price"].mean().round(2)
    avg_price.index = [f"{i} ★" for i in avg_price.index]
    st.bar_chart(avg_price)

with right2:
    st.subheader("Best value: top-rated and cheapest")
    best = (
        filtered[filtered["rating"] == filtered["rating"].max()]
        .nsmallest(10, "price")[["title", "price", "rating"]]
    )
    st.dataframe(best, hide_index=True, use_container_width=True)

st.divider()

# ---------- Data table ----------
st.subheader("All matching books")
st.dataframe(
    filtered[["title", "price", "rating", "availability", "url"]],
    hide_index=True,
    use_container_width=True,
    column_config={
        "title": "Title",
        "price": st.column_config.NumberColumn("Price", format="£%.2f"),
        "rating": st.column_config.NumberColumn("Rating", format="%d ★"),
        "availability": "Availability",
        "url": st.column_config.LinkColumn("Link", display_text="Open"),
    },
)

st.download_button(
    "Download filtered data (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8-sig"),
    file_name="books_filtered.csv",
    mime="text/csv",
)