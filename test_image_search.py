from image_search import ImageSearchEngine

def test_search():
    engine = ImageSearchEngine()
    try:
        results = engine.wikimedia_api.search_images('bò')
        print("Search results:", results)
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == '__main__':
    test_search()