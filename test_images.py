from image_search import ImageSearchEngine

print('🚀 Testing Enhanced Image Search Engine...')
engine = ImageSearchEngine()

# Test query
query = 'cà chua'
print(f'🔍 Searching for: {query}')

images = engine.search_images(query, 3)

print(f'\n✅ Results: {len(images)} images found')
print('=' * 60)

for i, img in enumerate(images):
    print(f'{i+1}. {img["title"]}')
    print(f'   URL: {img["url"][:80]}...')
    print(f'   Source: {img.get("source", "unknown")}')
    print(f'   Description: {img["description"][:60]}...')
    print()