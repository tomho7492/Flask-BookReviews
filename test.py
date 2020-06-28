import requests
import os

def main():
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"isbns": "0380795272", "key": "R02aORIUpZqnTScLahXQ"})
        data = res.json()
        rate = data['books'][0]['ratings_count']
        print(rate)


if __name__ == "__main__":
    main()