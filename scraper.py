import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
class ArticleListCache:
    def __init__(self, list_cache_file='article_list_cache.json'):
        self.list_cache_file = list_cache_file
        self.cache = self._load_cache()

    def _load_cache(self):
        """Load the list cache from file if it exists"""
        if os.path.exists(self.list_cache_file):
            try:
                with open(self.list_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {'articles': [], 'last_updated': None}
        return {'articles': [], 'last_updated': None}

    def _save_cache(self):
        """Save the list cache to file"""
        with open(self.list_cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_cached_list(self):
        """Get cached article list if it's recent enough (within 1 hour)"""
        if not self.cache['last_updated']:
            return None

        last_updated = datetime.fromisoformat(self.cache['last_updated'])
        if (datetime.now() - last_updated).total_seconds() < 3600:  # 1 hour
            return self.cache['articles']
        return None

    def update_cache(self, articles):
        """Update the article list cache"""
        self.cache['articles'] = articles
        self.cache['last_updated'] = datetime.now().isoformat()
        self._save_cache()


class ArticleCache:
    def __init__(self, cache_file='article_cache.json'):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self):
        """Load the cache from file if it exists"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cache(self):
        """Save the cache to file"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_article(self, title_link):
        """Get article from cache if it exists"""
        return self.cache.get(title_link)

    def add_article(self, title_link, article_data):
        """Add article to cache with timestamp"""
        article_data['cached_at'] = datetime.now().isoformat()
        self.cache[title_link] = article_data
        self._save_cache()

class NewsScraperBase:
    def __init__(self, url):
        self.url = url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching page: {e}")
            return None

    def parse_content(self, html_content):
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract all text content from the page
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Basic cleaning
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return lines

    def save_to_json(self, data, filename=None):
        if filename is None:
            filename = f'scrape_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # with open(filename, 'w', encoding='utf-8') as f:
        #     json.dump(data, f, ensure_ascii=False, indent=2)
        # print(f"Results saved to {filename}")

    def run(self):
        html_content = self.fetch_page()
        if html_content:
            content = self.parse_content(html_content)
            if content:
                self.save_to_json(content)
                return content
        return None

class NewsScraperEnhanced(NewsScraperBase):
    def parse_content(self, html_content):
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        news_blocks = soup.find_all('div', class_=['news-block highlighted', 'news-block'])

        parsed_news = []
        for block in news_blocks:
            if 'newsi-google-in-feed' not in block.get('class', []):  # Skip ad blocks
                news_item = {}

                # Get image information
                img_wrap = block.find('div', class_='img-wrap')
                if img_wrap and img_wrap.find('img'):
                    img = img_wrap.find('img')
                    news_item['image'] = {
                        'src': img.get('src', ''),
                        'alt': img.get('alt', ''),
                        'srcset': img.get('srcset', '')
                    }

                # Get title
                title_div = block.find('div', class_='title')
                if title_div and title_div.find('a'):
                    news_item['title'] = title_div.find('a').text.strip()
                    news_item['title_link'] = title_div.find('a')['href']

                # Get news excerpt
                excerpt_div = block.find('div', class_='news-excerpt')
                if excerpt_div:
                    date = excerpt_div.find('p')
                    news_item['date'] = date.text.strip() if date else ''
                    # Get text content excluding the date

                    # Remove the first element 'p' which contains the date
                    # and join the remaining elements as a string
                    # and strip any leading or trailing whitespace
                    # we can use lastChild to get the last text element
                    # $$('.news-excerpt')[0].lastChild.textContent.trim()
                    # excerpt_text = ''.join(str(content) for content in excerpt_div.contents[1:])
                    excerpt_text = excerpt_div.contents[-1].strip()
                    news_item['excerpt'] = excerpt_text.strip()

                # Get level links
                links_div = block.find('div', class_='fancy-buttons')
                if links_div:
                    news_item['level_links'] = [
                        {
                            'level': link.text.strip(),
                            'url': link['href']
                        }
                        for link in links_div.find_all('a')
                    ]

                parsed_news.append(news_item)

        return parsed_news

class ArticleDetailScraper(NewsScraperBase):
    def parse_content(self, html_content):
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        article = {}

        # Get title
        title_elem = soup.find('h1', class_='article-title')
        if title_elem:
            article['title'] = title_elem.text.strip()

        # Get image
        img_wrap = soup.find('div', class_='img-wrap')
        if img_wrap and img_wrap.find('a'):
            article['image_url'] = img_wrap.find('a')['href']

        # Get article content
        content_div = soup.find('div', id='nContent')
        if content_div:
            children = content_div.find_all(recursive=False)

            # Get date (first element)
            if children:
                article['date'] = children[0].text.strip()

            # Get main content (excluding date and last two elements)
            body_text = []
            for child in children[1:-2]:  # Skip date and last two elements
                body_text.append(child.text.strip())
            article['body'] = '\n'.join(body_text)

            # Get difficult words (second to last element)
            # difficult_words = {}
            # if len(children) >= 2:
            #     words_section = children[-2]
            #     words = words_section.find_all('strong')
            #     for word in words:
            #         if word.next_sibling:
            #             key = word.text.strip()
            #             # Get the text after the word and clean it
            #             value = word.next_sibling.text.strip()
            #             value = value.strip('()').strip()
            #             difficult_words[key] = value
            # article['difficult_words'] = difficult_words
            difficult_words = {}
            if len(children) >= 2:
                words_section = children[-2]  # Get the "Difficult words:" section
                for link in words_section.find_all('a', href=True):
                    word = link.find('strong')
                    if word and link.next_sibling:
                        key = word.text.strip()
                        # Get text after the link, which contains the definition
                        value = link.next_sibling.text.strip()
                        if value.startswith('(') and value.endswith(')'):
                            value = value[1:-1].strip()  # Remove parentheses
                        if key and value:  # Only add if both exist
                            difficult_words[key] = value.strip('(),.').strip()
            article['difficult_words'] = difficult_words
        return article

def scrape_article_detail(url):
    '''
    Scrape the article details from the given URL.
    :param url: URL of the article
    :type url: str
    :return: Article details
    :rtype: dict
    '''
    scraper = ArticleDetailScraper(url)
    article_data = scraper.run()
    return article_data
    # {
    #   "image_url": "https://www.newsinlevels.com/wp-content/uploads/2025/02/Depositphotos_321181526_L.jpg",
    #   "date": "11-02-2025 15:00",
    #   "body": "Latvia, Estonia, and Lithuania now get electricity from Europe, not Russia.\nBefore, they use Russian electricity for a long time. These countries do not want to use Russian electricity anymore. They want to be with Europe. They also feel safer now because they do not need Russia for power. Now, they have new power lines from Finland, Sweden, and Poland.\nOn Saturday, they stop using Russian electricity. On Sunday, they have a big party. Many important people came, like Ursula von der Leyen. In 2024, they tell Russia and Belarus about this change. They do not want any problems with Russia.",
    #   "difficult_words": {}
    # }

def scrape_article_list(url):
    '''
    Scrape the article list from the given URL.
    :param url: URL of the article list
    :type url: str
    :return: List of articles
    :rtype: list
    '''
    scraper = NewsScraperEnhanced(url)
    content = scraper.run()

    # if content:
    #     print(f"\nFound {len(content)} news articles")
    #     print("\nFirst article details:")
    #     print(json.dumps(content[0], indent=2, ensure_ascii=False))
    #     # second article
    #     print("\nSecond article details:")
    #     print(json.dumps(content[1], indent=2, ensure_ascii=False))
    return content

    #
    # First article details:
    # {
    #   "image": {
    #     "src": "https://www.newsinlevels.com/wp-content/uploads/2025/02/Depositphotos_321181526_L-300x150.jpg",
    #     "alt": "Baltic states don t get Russia’s electricity",
    #     "srcset": "https://www.newsinlevels.com/wp-content/uploads/2025/02/Depositphotos_321181526_L-300x150.jpg 300w, https://www.newsinlevels.com/wp-content/uploads/2025/02/Depositphotos_321181526_L-200x100.jpg 200w, https://www.newsinlevels.com/wp-content/uploads/2025/02/Depositphotos_321181526_L.jpg 600w"
    #   },
    #   "title": "Baltic states don’t get Russia’s electricity",
    #   "title_link": "https://www.newsinlevels.com/products/baltic-states-dont-get-russias-electricity-level-1/",
    #   "date": "11-02-2025 15:00",
    #   "excerpt": "<p>11-02-2025 15:00</p> Latvia, Estonia, and Lithuania now get electricity from Europe, not Russia. Before, they use Russian electricity for a long time....",
    #   "level_links": [
    #     {
    #       "level": "Level 1",
    #       "url": "https://www.newsinlevels.com/products/baltic-states-dont-get-russias-electricity-level-1"
    #     },
    #     {
    #       "level": "Level 2",
    #       "url": "https://www.newsinlevels.com/products/baltic-states-dont-get-russias-electricity-level-2"
    #     },
    #     {
    #       "level": "Level 3",
    #       "url": "https://www.newsinlevels.com/products/baltic-states-dont-get-russias-electricity-level-3"
    #     }
    #   ]
    # }

def scrape_article_basic(url):
    scraper = NewsScraperBase(url)
    content = scraper.run()

    if content:
        print("\nFirst 5 lines of extracted content:")
        for line in content[:5]:
            print(line)
    # Results saved to scrape_result_20250212_120209.json
    #
    # First 5 lines of extracted content:
    # English news and easy articles for students of English
    # World News for Students of English
    # Toggle navigation
    # Home
    # Level 1

def main():
    # url = input("Please enter the URL to scrape: ")
    url = 'https://www.newsinlevels.com'

    ######################################################## this is article detail scraper
    # cache = ArticleCache()
    #
    # # Example usage - basic scraper
    # # scrape_article_basic(url)
    #
    # # Example usage - enhanced scraper
    # content = scrape_article_list(url)
    #
    # # Process each article
    # for article in content:
    #     title_link = article['title_link']
    #
    #     # Check if article is in cache
    #     cached_article = cache.get_article(title_link)
    #     if cached_article:
    #         print(f"Loading cached article: {article['title']}")
    #         article['details'] = cached_article
    #     else:
    #         print(f"Scraping new article: {article['title']}")
    #         article_data = scrape_article_detail(title_link)
    #         article['details'] = article_data
    #         cache.add_article(title_link, article_data)


    # Example article URL
    # article_url = "https://www.newsinlevels.com/products/nigeria-wants-to-produce-oil-again-level-1/"
    # article_url = content[0]['title_link']
    # article_data = scrape_article_detail(article_url)
    # article_data = scrape_article_detail('https://www.newsinlevels.com/products/cheap-valentines-day-gifts-level-1/')

    # appen the article data to the list sd 'deltails'
    # content[0]['details'] = article_data
    # if article_data:
    #     # print(json.dumps(article_data, indent=2, ensure_ascii=False))
    #     print(json.dumps(content[0], indent=2, ensure_ascii=False))



    article_cache = ArticleCache()
    list_cache = ArticleListCache()

    # Try to get cached article list
    cached_list = list_cache.get_cached_list()
    # Try to get cached article list and compare
    cached_list = list_cache.get_cached_list()
    new_content = scrape_article_list(url)
    content = []

    if cached_list:
        print("Comparing with cached article list")
        cached_urls = {article['title_link'] for article in cached_list}

        # Check each new article
        for article in new_content:
            if article['title_link'] in cached_urls:
                print(f"Article exists in cache: {article['title']}")
                # Get the cached version
                content.append(next(a for a in cached_list if a['title_link'] == article['title_link']))
            else:
                print(f"New article found: {article['title']}")
                content.append(article)
    else:
        print("No cached list found, using all new articles")
        content = new_content

    # Update cache with latest content
    list_cache.update_cache(content)

    # Process each article
    for article in content:
        title_link = article['title_link']

        # Check if article is in cache
        cached_article = article_cache.get_article(title_link)
        if cached_article:
            print(f"Loading cached article: {article['title']}")
            article['details'] = cached_article
        else:
            print(f"Scraping new article: {article['title']}")
            article_data = scrape_article_detail(title_link)
            article['details'] = article_data
            article_cache.add_article(title_link, article_data)

    # Save results
    scraper = NewsScraperBase(url)
    scraper.save_to_json(content)

if __name__ == "__main__":
    main()



