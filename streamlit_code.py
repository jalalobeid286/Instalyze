import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import time
import re
import google.generativeai as genai
from insta_scraper2 import (extract_post_links, process_post,generate_prompt_from_data, get_digital_marketing_suggestions)
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import arabic_reshaper
from bidi.algorithm import get_display





st.set_page_config(
    page_title="Instagram Scraping Analysis",
    page_icon="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/120px-Instagram_logo_2016.svg.png"
)


def run_analysis(username):
    written_profiles = set()
    links = extract_post_links(username)
    for link in links:
        match = re.search(r"/(p|reel|tv)/([^/?#&]+)", link)
        if match:
            shortcode = match.group(2)
            clean_link = f"https://www.instagram.com/{match.group(1)}/{shortcode}/"
            process_post(clean_link, written_profiles)
            time.sleep(10)

    profile_csv = f"{username}_profile.csv"
    posts_csv = f"{username}_posts.csv"

    if not os.path.exists(profile_csv) or not os.path.exists(posts_csv):
        st.error("Profile or post data not found.")
        return None, None

    df1 = pd.read_csv(profile_csv)
    df = pd.read_csv(posts_csv)

    return df1, df

def plot_visualizations(df, df1):
    df.columns = df.columns.str.strip()
    from nltk.corpus import stopwords
    from collections import Counter
    import arabic_reshaper
    from bidi.algorithm import get_display

# Ensure text column exists
    df['Comments'] = df['Comments'].fillna('')

# Define stopwords


    follower_count = df1['Followers'].iloc[0]

    df['Number of Comments'] = pd.to_numeric(df['Number of Comments'], errors='coerce').fillna(0).astype(int)
    df['Likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
    df['Views'] = pd.to_numeric(df['Views'], errors='coerce').fillna(0).astype(int)
    df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.tz_localize(None)
    df['Engagement'] = df['Likes'] + df['Number of Comments']
    df['Engagement Rate (%)'] = df['Engagement'] / follower_count * 100
    df['Like-to-Comment Ratio'] = df['Likes'] / df['Number of Comments'].replace(0, 1)
    df['Week'] = df['Timestamp'].dt.isocalendar().week
    df['Year'] = df['Timestamp'].dt.isocalendar().year
    df['Year-Week'] = df['Year'].astype(str) + '-W' + df['Week'].astype(str)
    df['Month'] = df['Timestamp'].dt.to_period('M').astype(str)
    df['Hour'] = df['Timestamp'].dt.hour
    df['Caption Length'] = df['Caption'].apply(lambda x: len(x) if isinstance(x, str) else 0)
    df = df.drop_duplicates()
    st.dataframe(df)
    arabic_stopwords = set(stopwords.words('arabic'))
    english_stopwords = set(stopwords.words('english'))

    
# Most Common Word per Post
    def get_most_common_word(text):
       words = re.findall(r'\b\w+\b', str(text).lower())
       filtered = [w for w in words if w not in arabic_stopwords and w not in english_stopwords and len(w) > 2]
       if filtered:
           return Counter(filtered).most_common(1)[0][0]
       return "N/A"

    df['Top_Word'] = df['Comments'].apply(get_most_common_word)

# Evaluate post
    def evaluate_post(row):
      likes = row['Likes']
      views = row.get('Views', 0)
      sentiment = row.get('Sentiment', 'Neutral')
      if likes >= 1000 and sentiment == 'Positive':
          return 'Excellent Performance'
      elif likes >= 500 and sentiment != 'Negative':
          return 'Good Performance'
      elif sentiment == 'Negative':
          return 'Needs Improvement'
      return 'Average Performance'

    df['Evaluation'] = df.apply(evaluate_post, axis=1)

# Get top 8 words overall
    all_comments = df['Comments'].str.cat(sep=' ')
    def get_top_words(text, top_n=8):
      words = re.findall(r'\b\w+\b', str(text).lower())
      filtered = [w for w in words if w not in arabic_stopwords and w not in english_stopwords and len(w) > 2]
      return Counter(filtered).most_common(top_n)

    top_words = get_top_words(all_comments, top_n=8)
    
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

    df['Sentiment'] = df['Comments'].apply(analyze_sentiment_vader)

    fig, axs = plt.subplots(2, 3, figsize=(18, 10))

    sns.barplot(data=df.groupby('post_type')['Engagement'].mean().reset_index(), x='post_type', y='Engagement', ax=axs[0, 0])
    axs[0, 0].set_title('Average Engagement by Post Type')

    sns.barplot(data=df.groupby('Year-Week').size().reset_index(name='Post Count'), x='Year-Week', y='Post Count', ax=axs[0, 1])
    axs[0, 1].set_title('Posts per Week')
    axs[0, 1].tick_params(axis='x', rotation=45)

    sns.lineplot(data=df.groupby('Year-Week')['Engagement Rate (%)'].mean().reset_index(), x='Year-Week', y='Engagement Rate (%)', ax=axs[0, 2])
    axs[0, 2].set_title('Engagement Rate Over Weeks')
    axs[0, 2].tick_params(axis='x', rotation=45)

    sns.lineplot(data=df.groupby('Month')['Like-to-Comment Ratio'].mean().reset_index(), x='Month', y='Like-to-Comment Ratio', ax=axs[1, 0])
    axs[1, 0].set_title('Like-to-Comment Ratio Over Time')
    axs[1, 0].tick_params(axis='x', rotation=45)

    sns.lineplot(data=df.groupby(['post_type', 'Hour'])['Engagement'].mean().reset_index(), x='Hour', y='Engagement', hue='post_type', ax=axs[1, 1])
    axs[1, 1].set_title('Hourly Engagement by Post Type')

    sns.scatterplot(data=df, x='Caption Length', y='Engagement', hue='post_type', alpha=0.7, ax=axs[1, 2])
    axs[1, 2].set_title('Caption Length vs Engagement')

    st.pyplot(fig)

    # Add a second set of visualizations
    fig2, axes = plt.subplots(1, 3, figsize=(20, 6))

# 1. Sentiment Distribution
    sns.countplot(x='Sentiment', data=df, palette='coolwarm', ax=axes[0])
    axes[0].set_title('Sentiment Distribution in Comments', fontsize=14)
    axes[0].set_xlabel('Sentiment')
    axes[0].set_ylabel('Number of Posts')

# 2. Post Performance Evaluation
    sns.countplot(x='Evaluation', data=df, palette='viridis', ax=axes[1])
    axes[1].set_title('Post Performance Evaluation', fontsize=14)
    axes[1].set_xlabel('Evaluation')
    axes[1].tick_params(axis='x', rotation=20)

# 3. Top 8 Words Barplot
    words, counts = [], []
    for word, count in top_words:
      if re.search(r'[\u0600-\u06FF]', word):  # Arabic
        reshaped = arabic_reshaper.reshape(word)
        bidi_word = get_display(reshaped)
        words.append(bidi_word)
      else:
        words.append(word)
      counts.append(count)

    sns.barplot(x=counts, y=words, color='blue', ax=axes[2])
    axes[2].set_title('Top 8 Most Frequent Words')
    axes[2].set_xlabel('Frequency')
    axes[2].set_ylabel('Word')

    st.pyplot(fig2)


def main():
    
    st.markdown(
    """
    <div style='display: flex; align-items: center; margin-bottom: 30px;'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png' width='50' style='margin-right: 15px;'/>
        <span style='font-size: 2.5em; font-weight: bold;'>InstaScope: Decode. Analyze. Grow.</span>
    </div>
    """,
    unsafe_allow_html=True
    )
    username = st.text_input("Enter Instagram username (without @):")

    if st.button("Start Analysis"):
        with st.spinner("Scraping Instagram posts and analyzing..."):
            df1, df = run_analysis(username)
            if df1 is not None and df is not None:
                st.success("✅ Analysis Complete!")
                st.subheader("📌 Account Info")
                st.write(df1)

                st.subheader("📈 Engagement Visualizations")
                plot_visualizations(df, df1)

                
                prompt = generate_prompt_from_data(df)
               
                suggestions = get_digital_marketing_suggestions(prompt)
             
                try:
                  
                   suggestions = get_digital_marketing_suggestions(prompt)
                   
                   st.subheader("🎯 Marketing Suggestions")
                   st.write(suggestions)
                except Exception as e:
                   st.write("DEBUG: Inside except block")  # Check if this appears
                   st.error(f"Failed to get suggestions: {str(e)}")

                

               
    # عرض أسماء الفريق والمشرفة بأسفل الصفحة
     # --- تذييل بأسماء الفريق والمشرفة ---
    st.markdown("<div style='height:100px'></div>", unsafe_allow_html=True)

    # عرض أسماء الفريق والمشرفة بأسفل الصفحة
    st.markdown("---")
    st.markdown(
       """
       <div style="text-align: center; padding: 10px; font-size: 16px; font-weight: bold;">
           Project Team: Jalal Obeid · Ali Zalghout · Julia Al Sayed Kassem<br>
           Supervised by: Dr. Linda Mahmoudi
       </div>
       """, unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()