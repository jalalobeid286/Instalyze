import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import os
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import nltk
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import arabic_reshaper
from bidi.algorithm import get_display
import datetime
from collections import Counter
from nltk.corpus import stopwords
import matplotlib.font_manager as fm

def extract_post_links(username):
   

    TARGET_USERNAME = username


    chromedriver_path = r"C:\Users\user\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"  # استبدل بالمسار الصحيح للـchromedriver
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service)

    driver.get("https://www.instagram.com/")
    time.sleep(5)




    cookie_path = r"C:\Users\user\Downloads\scraping\cookies.json"
    if not os.path.exists(cookie_path) or os.path.getsize(cookie_path) == 0:
        print("❌ Cookie file is missing or empty!")
        driver.quit()
        exit()

    with open(r"C:\Users\user\Downloads\scraping\cookies.json", "r") as f:
        cookies = json.load(f)
        for cookie in cookies:
            if 'sameSite' in cookie: 
                if cookie['sameSite'] == 'unspecified':
                    cookie['sameSite'] = 'Strict'
            driver.add_cookie(cookie)


    time.sleep(5) 


    driver.get(f"https://www.instagram.com/{TARGET_USERNAME}/")
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
    return post_links

def process_post(url, written_profiles):
    import instaloader
    import requests
  


    INSTAGRAM_URL = url


    API_TOKEN = "write your API_TOKEN here"
    TASK_ID = "whrite your TASK_ID here"


    
    match = re.search(r"/(reel|p|tv)/([^/?]+)", INSTAGRAM_URL)
    if not match:
        print("❌ Invalid Instagram URL format.")
        exit()
    shortcode = match.group(2)

    print("\n📌 Extracting post details...")

    L = instaloader.Instaloader()


    with open(r"C:\Users\user\Downloads\scraping\cookies.json", "r") as f:
        cookies = json.load(f)


    for cookie in cookies:
        if 'name' in cookie and 'value' in cookie:
            L.context._session.cookies.set(cookie['name'], cookie['value'])


    post = instaloader.Post.from_shortcode(L.context, shortcode)
    username = post.owner_username
    profile = instaloader.Profile.from_username(L.context, username)

    caption = post.caption or "No caption"
    hashtags = re.findall(r"#\w+", caption)
    views = post.video_view_count if post.is_video else None
    likes = post.likes if not post.is_video or post.likes != post.video_view_count else None
    timestamp = post.date_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    post_type = "Video" if post.is_video else "Photo"
    post_id = post.mediaid
    location = post.location.name if post.location else "No location"
    tags = post.tagged_users if post.tagged_users else "No tagged users"
    video_duration = post.video_duration if post.is_video else None
    Comments_count= post.comments 
    mentions = re.findall(r"@(\w+)", caption)
    followers= profile.followers
    Bio= profile.biography
    nb_posts=profile.mediacount
    following=profile.followees

    input_payload = {
        "directUrls": [INSTAGRAM_URL],
        "includeNestedComments": False,     
        "isNewestComments": True,          
        "resultsLimit": 1000               
    }


    start_url = f"https://api.apify.com/v2/actor-tasks/{TASK_ID}/runs?token={API_TOKEN}"
    start_response = requests.post(start_url, json=input_payload)
    start_data = start_response.json()

    if 'data' not in start_data:
        print("❌ Failed to start task. Full response:")
        print(start_data)
        exit()

    run_id = start_data['data']['id']
    


    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={API_TOKEN}"
    while True:
        time.sleep(5)
        status_response = requests.get(status_url)
        status_data = status_response.json()
        status = status_data.get('data', {}).get('status')
        print(f"⏳ Status: {status}")
        if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            break

    if status != "SUCCEEDED":
        print("❌ Task failed or was aborted.")
        exit()


    dataset_id = status_data['data']['defaultDatasetId']
    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={API_TOKEN}&clean=true"
    items_response = requests.get(items_url)
    comments_data = items_response.json() 
    import csv
    profile_csv = f"{username}_profile.csv"
    if username not in written_profiles:
      with open(profile_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["username","Followers", "Following", "Bio", "Number of Posts"])
        writer.writerow([username,followers, following, Bio, nb_posts])
      written_profiles.add(username)


    posts_csv = f"{username}_posts.csv"
    file_exists = os.path.isfile(posts_csv)

    with open(posts_csv, mode='a', newline='', encoding='utf-8') as file:
      writer = csv.writer(file)

   
      if not file_exists:
         writer.writerow([
            "Post ID", "Views", "Caption", "Hashtags", "Likes", "Timestamp",
            "Comments", "Number of Comments", "Mentions"," post_type"
        ])

    
      comment_texts = [item.get("text", "") for item in comments_data]
      comments_combined = " || ".join(comment_texts)

      writer.writerow([
          post_id, views, caption, ", ".join(hashtags), likes, timestamp,
          comments_combined, Comments_count, ", ".join(mentions), post_type
      ])

   
       
        
    return 
API_KEY ="Write your API_KEY here"

genai.configure(api_key=API_KEY)

    
 
def generate_prompt_from_data(df):
    # Create a simple summary or formatted string from CSV data to send to AI
    # For example, describe the main columns and some sample rows
        summary = "You are a digital marketing expert. Analyze the following Instagram performance data and give me actionable marketing suggestions.\n\n"
        summary += "Columns:\n"
        for col in df.columns:
            summary += f"- {col}\n"
        summary += "\nSample data:\n"
        sample = df.to_string(index=False)
        summary += sample + "\n"
        summary += "\nPlease provide clear, concise digital marketing recommendations based on this data(thesenare all the page's posts), do not give adjustments for the data in the csv or the format of it just marketing recommendations based on the data in the csv"
        return summary

def get_digital_marketing_suggestions(prompt):
        genai.configure(api_key="Write your API_KEY here")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt])
        return response.text
def main():
    USERNAME = input("Enter Instagram username: ")
    written_profiles = set() 
    links = extract_post_links(USERNAME)
    for link in links:
        # Clean the link format for Apify
        match = re.search(r"/(p|reel|tv)/([^/?#&]+)", link)
        if match:
            shortcode = match.group(2)
            clean_link = f"https://www.instagram.com/{match.group(1)}/{shortcode}/"
            process_post(clean_link, written_profiles)
            time.sleep(10)
        else:
            print(f"❌ Skipping invalid link: {link}")
    
    profile_csv = f"{USERNAME}_profile.csv"
    posts_csv = f"{USERNAME}_posts.csv"

   
    try:
        df = pd.read_csv(posts_csv)
        df1 = pd.read_csv(profile_csv)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return
    


    df = pd.read_csv(posts_csv)
    df1 = pd.read_csv(profile_csv)
    df.columns = df.columns.str.strip()


    follower_count = df1['Followers'].iloc[0]  


    df['Number of Comments'] = pd.to_numeric(df['Number of Comments'], errors='coerce').fillna(0).astype(int)
    df['Likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df['Timestamp'] = df['Timestamp'].dt.tz_localize(None)  
    df['Engagement'] = df['Likes'] + df['Number of Comments']
    df['Like Rate (%)'] = df['Likes'] / follower_count * 100
    df['Comment Rate (%)'] = df['Number of Comments'] / follower_count * 100
    df['Engagement Rate (%)'] = df['Engagement'] / follower_count * 100
    df['Like-to-Comment Ratio'] = df['Likes'] / df['Number of Comments'].replace(0, 1)


    df['Week'] = df['Timestamp'].dt.isocalendar().week
    df['Year'] = df['Timestamp'].dt.isocalendar().year
    df['Year-Week'] = df['Year'].astype(str) + '-W' + df['Week'].astype(str)


    df['Month'] = df['Timestamp'].dt.to_period('M').astype(str)


    fig, axs = plt.subplots(2, 3, figsize=(18, 10))


    engagement_by_type = df.groupby('post_type')['Engagement'].mean().reset_index()
    sns.barplot(data=engagement_by_type, x='post_type', y='Engagement', ax=axs[0, 0], legend=False)
    axs[0, 0].set_title('Average Engagement by Post Type')
    axs[0, 0].set_xlabel('Post Type')
    axs[0, 0].set_ylabel('Average Engagement')


    weekly_posts = df.groupby('Year-Week').size().reset_index(name='Post Count')
    sns.barplot(data=weekly_posts, x='Year-Week', y='Post Count', color='skyblue', ax=axs[0, 1])
    axs[0, 1].set_title('Number of Posts per Week')
    axs[0, 1].set_xlabel('Week')
    axs[0, 1].set_ylabel('Posts')
    axs[0, 1].tick_params(axis='x', rotation=45)


    weekly_er = df.groupby('Year-Week')['Engagement Rate (%)'].mean().reset_index()
    sns.lineplot(data=weekly_er, x='Year-Week', y='Engagement Rate (%)', marker='o', color='orange', ax=axs[0, 2])
    axs[0, 2].set_title('Weekly Average Engagement Rate')
    axs[0, 2].set_xlabel('Week')
    axs[0, 2].set_ylabel('Engagement Rate (%)')
    axs[0, 2].tick_params(axis='x', rotation=45)


    monthly_ratio = df.groupby('Month')['Like-to-Comment Ratio'].mean().reset_index()
    sns.lineplot(data=monthly_ratio, x='Month', y='Like-to-Comment Ratio', marker='o', color='orange', ax=axs[1, 0])
    axs[1, 0].set_title('Like-to-Comment Ratio Over Time')
    axs[1, 0].set_xlabel('Month')
    axs[1, 0].set_ylabel('Likes per Comment')
    axs[1, 0].tick_params(axis='x', rotation=45)


    df['Hour'] = df['Timestamp'].dt.hour
    hourly_engagement = df.groupby(['post_type', 'Hour'])['Engagement'].mean().reset_index()
    sns.lineplot(data=hourly_engagement, x='Hour', y='Engagement', hue='post_type', marker='o', ax=axs[1, 1])
    axs[1, 1].set_title('Hourly Engagement by Post Type')
    axs[1, 1].set_xlabel('Hour of Day')
    axs[1, 1].set_ylabel('Average Engagement')
    axs[1, 1].set_xticks(range(0, 24))


    df['Caption Length'] = df['Caption'].apply(lambda x: len(x) if isinstance(x, str) else 0)
    sns.scatterplot(data=df, x='Caption Length', y='Engagement', hue='post_type', alpha=0.7, ax=axs[1, 2])
    axs[1, 2].set_title('Caption Length vs Engagement by Post Type')
    axs[1, 2].set_xlabel('Caption Length (characters)')
    axs[1, 2].set_ylabel('Engagement')


    plt.tight_layout()
    plt.show()

    account_info=pd.read_csv(profile_csv)
    posts_info=pd.read_csv(posts_csv)
    posts_info['Comments']=posts_info['Comments'].fillna("")
#--------
    analyzer = SentimentIntensityAnalyzer()

    def analyze_sentiment_vader(text):
        try:
          reshaped_text = arabic_reshaper.reshape(str(text))
          bidi_text = get_display(reshaped_text)
          sentiment_score = analyzer.polarity_scores(bidi_text)
          compound_score = sentiment_score['compound']
          if compound_score > 0.01:
            return 'Positive'
          elif compound_score < -0.01:
            return 'Negative'
          else:
            return 'Neutral'
        except:
          return 'Neutral'

    posts_info['Sentiment'] = posts_info['Comments'].apply(analyze_sentiment_vader)

# ----------------------------
# 3. Most Common Word per Post
# ----------------------------

    arabic_stopwords = set(stopwords.words('arabic'))
    english_stopwords = set(stopwords.words('english'))

    def get_most_common_word(text):
        try:
            words = re.findall(r'\b\w+\b', str(text).lower())
            filtered_words = [word for word in words if word not in arabic_stopwords and word not in english_stopwords and len(word) > 2]
            if filtered_words:
                most_common = Counter(filtered_words).most_common(1)
                return most_common[0][0]
            else:
                return "N/A"
        except:
            return "N/A"

    posts_info['Top_Word'] = posts_info['Comments'].apply(get_most_common_word)

# ----------------------------
# 4. Post Evaluation
# ----------------------------

    def evaluate_post(row):
        likes = row['Likes']
        views = row['Views']
        sentiment = row['Sentiment']

        if likes >= 1000 and sentiment == 'Positive':
            return 'Excellent Performance'
        elif likes >= 500 and sentiment != 'Negative':
            return 'Good Performance'
        elif sentiment == 'Negative':
            return 'Needs Improvement'
        else:
            return 'Average Performance'

    def suggest_improvement(row):
        if row['Sentiment'] == 'Negative':
            return 'Consider improving content quality or engaging more with the audience.'
        elif row['Likes'] < 300:
            return 'Try posting at different times or using better hashtags.'
        elif row['Views'] < 1000:
            return 'Use stories or reels to increase reach.'
        else:
            return 'Keep up the good work!'

    posts_info['Evaluation'] = posts_info.apply(evaluate_post, axis=1)
    posts_info['Suggestion'] = posts_info.apply(suggest_improvement, axis=1)

# ----------------------------
# 5. Most Common Words in All Comments (Overall)
# ----------------------------

    all_comments = posts_info['Comments'].str.cat(sep=' ')

    def get_top_words(text, top_n=8):
        words = re.findall(r'\b\w+\b', str(text).lower())
        filtered = [w for w in words if w not in arabic_stopwords and w not in english_stopwords and len(w) > 2]
        return Counter(filtered).most_common(top_n)

    top_words = get_top_words(all_comments, top_n=8)

# ----------------------------
# 6. Export Results to CSV (UTF-8 for Arabic compatibility)
# ----------------------------

    today = datetime.date.today().strftime('%Y-%m-%d')
    output_filename = f'analyzed_posts_{today}.csv'
    posts_info.to_csv(output_filename, index=False, encoding='utf-8-sig')

# ----------------------------
# 7–8. Combined Visualization in One Page (3 subplots)
# ----------------------------

    plt.rcParams['font.family'] = 'Arial'
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

# 1. Sentiment Distribution
    sns.countplot(x='Sentiment', data=posts_info, palette='coolwarm', ax=axes[0])
    axes[0].set_title('Sentiment Distribution in Comments', fontsize=14)
    axes[0].set_xlabel('Sentiment', fontsize=12)
    axes[0].set_ylabel('Number of Posts', fontsize=12)
    axes[0].tick_params(axis='x', rotation=0)

# 2. Post Performance Evaluation
    sns.countplot(x='Evaluation', data=posts_info, palette='viridis', ax=axes[1])
    axes[1].set_title('Post Performance Evaluation', fontsize=14)
    axes[1].set_xlabel('Evaluation', fontsize=12)
    axes[1].set_ylabel('Number of Posts', fontsize=12)
    axes[1].tick_params(axis='x', rotation=30)

# 3. Top 8 Words
    words = []
    counts = []

    for word, count in top_words:
        if re.search(r'[\u0600-\u06FF]', word):  # If Arabic
            reshaped = arabic_reshaper.reshape(word)
            bidi_word = get_display(reshaped)
            words.append(bidi_word)
        else:
            words.append(word)
        counts.append(count)

    sns.barplot(x=counts, y=words, color='blue', ax=axes[2])
    axes[2].set_title('Top 8 Most Frequent Words', fontsize=14)
    axes[2].set_xlabel('Frequency', fontsize=12)
    axes[2].set_ylabel('Word', fontsize=12)

    plt.tight_layout()
    plt.savefig('all_three_visualizations.png')
    plt.show()

    load_dotenv()

# Set your Gemini API key from environment variables     

    prompt = generate_prompt_from_data(df)
    print("Sending prompt to Gemini API...")
    suggestions = get_digital_marketing_suggestions(prompt)
    print("\nDigital Marketing Suggestions:\n")
    print(suggestions)     
#-----------
if __name__ == "__main__": 
    main()



