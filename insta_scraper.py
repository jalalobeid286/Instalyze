import json
import os
import re
import time
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk
import streamlit as st
import csv

nltk.download('stopwords')

def extract_post_links(username):
    chromedriver_path = r"C:\Users\user\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service)

    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(5)

    cookie_path = r"C:\Users\user\Downloads\scraping\cookies.json"
    if not os.path.exists(cookie_path) or os.path.getsize(cookie_path) == 0:
        st.error("❌ Cookie file is missing or empty!")
        driver.quit()
        return []

    with open(cookie_path, "r") as f:
        cookies = json.load(f)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception:
                continue

    driver.refresh()
    time.sleep(5)

    post_links = set()
    scroll_pause = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        links = driver.find_elements(By.XPATH, '//a[contains(@href, "/p/") or contains(@href, "/reel/") or contains(@href, "/tv/")]')
        for link in links:
            href = link.get_attribute("href")
            post_links.add(href)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.quit()
    return list(post_links)

def process_post(url, written_profiles):
    import instaloader

    API_TOKEN = "apify_api_KnwzUftqerpeinIehOIk26r745Bdow3yLFjv"
    TASK_ID = "obxdFNXezzGyQSXQc"

    match = re.search(r"/(reel|p|tv)/([^/?]+)", url)
    if not match:
        st.warning("⚠️ Invalid post URL.")
        return False
    shortcode = match.group(2)

    L = instaloader.Instaloader()
    with open(r"C:\Users\user\Downloads\scraping\cookies.json", "r") as f:
        cookies = json.load(f)
    for cookie in cookies:
        if 'name' in cookie and 'value' in cookie:
            L.context._session.cookies.set(cookie['name'], cookie['value'])

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        username = post.owner_username
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return False

    caption = post.caption or "No caption available"
    hashtags = re.findall(r"#\w+", caption)
    views = post.video_view_count if post.is_video else None
    likes = post.likes if not post.is_video or post.likes != post.video_view_count else None
    timestamp = post.date_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    post_type = "Video" if post.is_video else "Image"
    post_id = post.mediaid
    location = post.location.name if post.location else "No location"
    mentions = re.findall(r"@(\w+)", caption)
    followers = profile.followers
    bio = profile.biography
    nb_posts = profile.mediacount
    following = profile.followees
    comments_count = post.comments

    input_payload = {
        "directUrls": [url],
        "includeNestedComments": False,
        "isNewestComments": True,
        "resultsLimit": 1000
    }

    start_url = f"https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs?token={API_TOKEN}"
    start_response = requests.post(start_url, json=input_payload)

    if start_response.status_code != 201:
        st.error(f"❌ Failed to start Apify task for post: {url}")
        return False

    start_data = start_response.json()
    run_id = start_data['data']['id']
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={API_TOKEN}"

    while True:
        time.sleep(5)
        status_response = requests.get(status_url)
        status_data = status_response.json()
        status = status_data.get('data', {}).get('status')
        st.info(f"ℹ️ Apify task status: {status}")
        if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            break

    if status != "SUCCEEDED":
        st.error("❌ Apify task failed or timed out.")
        return False

    dataset_id = status_data['data']['defaultDatasetId']
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_TOKEN}&clean=true"
    items_response = requests.get(items_url)
    comments_data = items_response.json()

    profile_csv = f"{username}_profile.csv"
    if username not in written_profiles:
        with open(profile_csv, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Username", "Followers", "Following", "Bio", "Posts Count"])
            writer.writerow([username, followers, following, bio, nb_posts])
        written_profiles.add(username)

    posts_csv = f"{username}_posts.csv"
    file_exists = os.path.isfile(posts_csv)

    with open(posts_csv, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "Post ID", "Views", "Caption", "Hashtags", "Likes", "Publish Date",
                "Comments", "Comments Count", "Mentions", "Post Type"
            ])

        comment_texts = [item.get("text", "") for item in comments_data]
        comments_combined = " || ".join(comment_texts)

        writer.writerow([
            post_id, views, caption, ", ".join(hashtags), likes, timestamp,
            comments_combined, comments_count, ", ".join(mentions), post_type
        ])
    
    return True

def analyze_and_show(username):
    profile_csv = f"{username}_profile.csv"
    posts_csv = f"{username}_posts.csv"

    if not os.path.exists(profile_csv) or not os.path.exists(posts_csv):
        st.error("📁 Required files are missing. Please extract the data first.")
        return

    df = pd.read_csv(posts_csv)
    df1 = pd.read_csv(profile_csv)

    follower_count = df1['Followers'].iloc[0]
    total_posts = df1['Posts Count'].iloc[0]

    df['Comments Count'] = pd.to_numeric(df['Comments Count'], errors='coerce').fillna(0).astype(int)
    df['Likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
    df['Publish Date'] = pd.to_datetime(df['Publish Date']).dt.tz_localize(None)
    df['Engagement'] = df['Likes'] + df['Comments Count']
    df['Like Rate (%)'] = df['Likes'] / follower_count * 100
    df['Comment Rate (%)'] = df['Comments Count'] / follower_count * 100

    st.markdown("## 📈 Account Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Followers", f"{follower_count:,}")
    col2.metric("Total Posts", total_posts)
    col3.metric("Average Engagement", f"{df['Engagement'].mean():.2f}")

    with st.expander("🔍 Show Post Details"):
        st.dataframe(df)

    st.markdown("## 📊 Engagement Over Time")
    plt.figure(figsize=(10,5))
    sns.lineplot(x='Publish Date', y='Engagement', data=df)
    plt.title("Engagement Over Time")
    plt.xlabel("Date")
    plt.ylabel("Engagement (Likes + Comments)")
    st.pyplot(plt)
    plt.clf()

    analyzer = SentimentIntensityAnalyzer()
    df['Comments'] = df['Comments'].fillna("")
    df['Sentiment Score'] = df['Comments'].apply(lambda text: analyzer.polarity_scores(text)['compound'] if text else 0)

    def classify_sentiment(score):
        if score >= 0.05:
            return "Positive"
        elif score <= -0.05:
            return "Negative"
        else:
            return "Neutral"

    df['Sentiment Category'] = df['Sentiment Score'].apply(classify_sentiment)

    st.markdown("## 📝 Sentiment Analysis of Comments")
    sentiment_counts = df['Sentiment Category'].value_counts()
    fig, ax = plt.subplots()
    sns.barplot(x=sentiment_counts.index, y=sentiment_counts.values, palette="viridis", ax=ax)
    ax.set_xlabel("Sentiment Type")
    ax.set_ylabel("Number of Posts")
    st.pyplot(fig)
    plt.clf()

    st.markdown("## 💡 Recommendations and Suggestions")
    suggestions = []

    avg_engagement = df['Engagement'].mean()
    if avg_engagement < 100:
        suggestions.append("📉 Engagement rate is low, consider improving content quality or using more attractive hashtags.")
    else:
        suggestions.append("✅ Engagement rate is good, keep up the current strategies.")

    negative_ratio = (df['Sentiment Category'] == 'Negative').mean()
    if negative_ratio > 0.3:
        suggestions.append("⚠️ High negative comments ratio, review content and feedback to address issues.")
    else:
        suggestions.append("😊 Negative comments ratio is low, good communication with the audience.")

    for sug in suggestions:
        st.info(sug)

st.title("Instagram Account Analysis and Post Evaluation")

username = st.text_input("Enter Instagram username (without @):")

if st.button("Extract Post Links"):
    if username:
        with st.spinner("⏳ Extracting post links..."):
            post_links = extract_post_links(username)
        st.success(f"✅ Extracted {len(post_links)} post links.")
        st.session_state['post_links'] = post_links
    else:
        st.error("Please enter a username.")

if 'post_links' in st.session_state and st.session_state['post_links']:
    st.write("### Post Links:")
    for link in st.session_state['post_links']:
        st.write(link)

    if st.button("Fetch Post Data and Comments"):
        written_profiles = set()
        success_count = 0
        for link in st.session_state['post_links']:
            with st.spinner(f"⏳ Processing post: {link}"):
                success = process_post(link, written_profiles)
                if success:
                    success_count += 1
        st.success(f"✅ Successfully processed {success_count} posts.")

if username and st.button("Show Analysis and Recommendations"):
    analyze_and_show(username)


