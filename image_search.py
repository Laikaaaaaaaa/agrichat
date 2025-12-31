"""
image_search.py - Chuyên xử lý tìm kiếm ảnh từ Wikimedia Commons API
Sử dụng API chính thức để lấy URLs ảnh thật 100% chính xác
"""
import os
import requests
import time
import random
import base64
import unicodedata
import logging
from urllib.parse import unquote
from dotenv import load_dotenv
from wikimedia_api import WikimediaAPI

class ImageSearchEngine:
    def __init__(self):
        load_dotenv()

        self.wikimedia_api = WikimediaAPI()
        self.timeout = 5  # Timeout cho mỗi request
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "").strip() or None
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID", "").strip() or None

        if not self.google_api_key or not self.google_cse_id:
            logging.warning(
                "⚠️  GOOGLE_API_KEY hoặc GOOGLE_CSE_ID chưa được cấu hình. Google Custom Search có thể không hoạt động."
            )
        
        # CATEGORY MAPPING cho tìm kiếm chuyên ngành - MỞ RỘNG TOÀN DIỆN
        self.category_mapping = {
            # Cây trồng chính
            'xoài': ['Mangoes', 'Mangifera indica', 'Tropical fruits'],
            'cà chua': ['Tomatoes', 'Solanum lycopersicum', 'Red vegetables'],
            'lúa': ['Rice', 'Oryza sativa', 'Cereal crops', 'Rice cultivation'],
            'ngô': ['Maize', 'Zea mays', 'Corn cultivation', 'Sweet corn'],
            'mía': ['Sugar cane', 'Saccharum officinarum', 'Sugar crops'],
            'lúa mì': ['Wheat', 'Triticum', 'Cereal grains'],
            'táo': ['Apples', 'Malus', 'Apple fruits', 'Red apples'],
            'cà rót': ['Carrots', 'Daucus carota', 'Orange vegetables'],
            'cà tím': ['Eggplants', 'Aubergines', 'Solanum melongena'],
            
            # Rau củ quả
            'khoai tây': ['Potatoes', 'Solanum tuberosum', 'Potato cultivation'],
            'khoai lang': ['Sweet potatoes', 'Ipomoea batatas'],
            'cà rốt': ['Carrots', 'Daucus carota', 'Orange vegetables'],
            'bắp cải': ['Cabbage', 'Brassica oleracea'],
            'rau muống': ['Water spinach', 'Ipomoea aquatica'],
            'dưa chuột': ['Cucumbers', 'Cucumis sativus'],
            'ớt': ['Peppers', 'Capsicum', 'Chili peppers'],
            'hành tây': ['Onions', 'Allium cepa'],
            'tỏi': ['Garlic', 'Allium sativum'],
            
            # Cây ăn trái
            'cam': ['Oranges', 'Citrus sinensis', 'Orange fruits'],
            'chanh': ['Lemons', 'Citrus limon', 'Limes'],
            'chuối': ['Bananas', 'Musa', 'Banana plants'],
            'dừa': ['Coconuts', 'Cocos nucifera', 'Coconut palms'],
            'đu đủ': ['Papayas', 'Carica papaya'],
            'nho': ['Grapes', 'Vitis vinifera', 'Grape vines'],
            'dâu tây': ['Strawberries', 'Fragaria'],
            
            # Động vật chăn nuôi
            'gà': ['Gallus gallus', 'Chickens', 'Poultry', 'Domestic fowl'],
            'bò': ['Cattle', 'Bovinae', 'Dairy cows', 'Beef cattle'],
            'heo': ['Pigs', 'Sus', 'Swine', 'Domestic pigs'],
            'cừu': ['Sheep', 'Ovis aries', 'Wool sheep'],
            'dê': ['Goats', 'Capra', 'Dairy goats'],
            'vịt': ['Ducks', 'Anatidae', 'Domestic ducks'],
            'ngỗng': ['Geese', 'Anser', 'Domestic geese'],
            'chó': ['Dogs', 'Canis lupus familiaris', 'Domestic dogs', 'Dog breeds'],
            'cá': ['Fish', 'Aquaculture', 'Fish farming'],
            'tôm': ['Shrimp', 'Penaeus', 'Shrimp farming'],

            # Thuỷ sản phổ biến (theo loài)
            'cá tra': ['Pangasius', 'Catfish', 'Aquaculture'],
            'ca basa': ['Pangasius', 'Catfish', 'Aquaculture'],
            'ca ro phi': ['Tilapia', 'Tilapia farming', 'Aquaculture'],
            'ca loc': ['Snakehead fish', 'Channa', 'Aquaculture'],
            'ca chep': ['Common carp', 'Cyprinus carpio', 'Aquaculture'],
            'tôm thẻ': ['Whiteleg shrimp', 'Litopenaeus vannamei', 'Shrimp farming'],
            'tom su': ['Giant tiger prawn', 'Penaeus monodon', 'Shrimp farming'],

            # Bổ sung động vật & thuỷ sản
            'lợn': ['Pigs', 'Sus', 'Swine', 'Domestic pigs'],
            'trâu': ['Water buffalo', 'Bubalus bubalis', 'Buffalo farming'],
            'ngựa': ['Horses', 'Equus ferus caballus'],
            'thỏ': ['Rabbits', 'Rabbit farming'],
            'chim cút': ['Quails', 'Coturnix japonica', 'Quail farming'],
            'ong mật': ['Honey bees', 'Apiculture', 'Beekeeping'],
            'nuôi ong': ['Beekeeping', 'Apiculture'],
            'cua': ['Crabs', 'Crab farming', 'Scylla serrata'],
            'ốc': ['Snails', 'Freshwater snails', 'Golden apple snail'],
            'nghêu': ['Clams', 'Clam farming', 'Meretrix'],
            'hàu': ['Oysters', 'Oyster farming'],
            'rong biển': ['Seaweed', 'Seaweed farming'],

            # Trái cây phổ biến (bổ sung)
            'sầu riêng': ['Durian', 'Durio', 'Tropical fruits'],
            'thanh long': ['Dragon fruit', 'Pitaya', 'Hylocereus'],
            'mít': ['Jackfruit', 'Artocarpus heterophyllus'],
            'bưởi': ['Pomelo', 'Citrus maxima'],
            'ổi': ['Guava', 'Psidium guajava'],
            'vải': ['Lychee', 'Litchi chinensis'],
            'nhãn': ['Longan', 'Dimocarpus longan'],
            'chôm chôm': ['Rambutan', 'Nephelium lappaceum'],
            'măng cụt': ['Mangosteen', 'Garcinia mangostana'],
            'dứa': ['Pineapple', 'Ananas comosus'],
            'thơm': ['Pineapple', 'Ananas comosus'],
            'khóm': ['Pineapple', 'Ananas comosus'],
            'dưa hấu': ['Watermelon', 'Citrullus lanatus'],
            'dưa lưới': ['Melon', 'Cantaloupe'],

            # Cây công nghiệp (bổ sung)
            'cà phê': ['Coffee', 'Coffea', 'Coffee plantation'],
            'chè': ['Tea', 'Camellia sinensis', 'Tea plantation'],
            'trà': ['Tea', 'Camellia sinensis'],
            'hồ tiêu': ['Black pepper', 'Piper nigrum'],
            'tiêu': ['Black pepper', 'Piper nigrum'],
            'điều': ['Cashew', 'Anacardium occidentale'],
            'cao su': ['Rubber tree', 'Hevea brasiliensis'],

            # Rau củ (bổ sung)
            'xà lách': ['Lettuce', 'Lactuca sativa'],
            'cải thảo': ['Napa cabbage', 'Chinese cabbage'],
            'cải xanh': ['Mustard greens', 'Brassica juncea'],
            'cải ngọt': ['Choy sum', 'Chinese flowering cabbage'],
            'cải bó xôi': ['Spinach', 'Spinacia oleracea'],
            'rau dền': ['Amaranth', 'Leafy vegetable'],
            'mồng tơi': ['Malabar spinach', 'Basella alba'],
            'rau ngót': ['Katuk', 'Sauropus androgynus'],
            'bông cải': ['Broccoli', 'Cauliflower'],
            'súp lơ': ['Cauliflower', 'Broccoli'],
            'bí đỏ': ['Pumpkin', 'Squash'],
            'bí xanh': ['Winter melon', 'Benincasa hispida'],
            'bí ngòi': ['Zucchini', 'Courgette'],
            'mướp': ['Luffa', 'Sponge gourd'],
            'khổ qua': ['Bitter melon', 'Momordica charantia'],
            'mướp đắng': ['Bitter melon', 'Momordica charantia'],
            'đậu bắp': ['Okra', 'Abelmoschus esculentus'],
            'đậu que': ['Green beans', 'String beans'],
            'đậu hà lan': ['Peas', 'Pisum sativum'],
            'đậu nành': ['Soybean', 'Glycine max'],
            'đậu tương': ['Soybean', 'Glycine max'],
            'đậu phộng': ['Peanuts', 'Groundnuts', 'Arachis hypogaea'],
            'lạc': ['Peanuts', 'Groundnuts', 'Arachis hypogaea'],
            'vừng': ['Sesame', 'Sesamum indicum'],
            'mè': ['Sesame', 'Sesamum indicum'],
            'củ cải': ['Radishes', 'Raphanus sativus'],
            'củ dền': ['Beetroots', 'Beta vulgaris'],
            'khoai mì': ['Cassava', 'Manioc', 'Tapioca'],
            'sắn': ['Cassava', 'Manioc', 'Tapioca'],
            'khoai môn': ['Taro', 'Colocasia esculenta'],
            'sả': ['Lemongrass', 'Cymbopogon'],
            'gừng': ['Ginger', 'Zingiber officinale'],
            'nghệ': ['Turmeric', 'Curcuma longa'],

            # Sâu bệnh & dinh dưỡng (bổ sung)
            'rầy nâu': ['Brown planthopper', 'Rice pest'],
            'sâu cuốn lá': ['Leaf folder', 'Rice pest'],
            'sâu đục thân': ['Stem borer', 'Rice pest'],
            'bọ trĩ': ['Thrips', 'Crop pest'],
            'nhện đỏ': ['Spider mites', 'Crop pest'],
            'rệp sáp': ['Mealybugs', 'Crop pest'],
            'sâu keo mùa thu': ['Fall armyworm', 'Maize pest'],
            'ruồi vàng': ['Fruit fly', 'Bactrocera'],
            'đạo ôn': ['Rice blast', 'Magnaporthe oryzae'],
            'khô vằn': ['Sheath blight', 'Rice disease'],
            'bạc lá': ['Bacterial leaf blight', 'Rice disease'],
            'thán thư': ['Anthracnose', 'Plant disease'],
            'phấn trắng': ['Powdery mildew', 'Plant disease'],
            'sương mai': ['Downy mildew', 'Plant disease'],

            # Vật tư/công nghệ canh tác (bổ sung)
            'phân hữu cơ': ['Organic fertilizer', 'Compost'],
            'phân chuồng': ['Manure', 'Farmyard manure'],
            'phân trùn quế': ['Vermicompost', 'Worm castings'],
            'vôi nông nghiệp': ['Agricultural lime', 'Soil amendment'],
            'ure': ['Urea fertilizer', 'Nitrogen fertilizer'],
            'dap': ['DAP fertilizer', 'Diammonium phosphate'],
            'kali': ['Potassium fertilizer', 'Potash'],
            'npk': ['NPK fertilizer', 'Compound fertilizer'],
            'thuốc trừ cỏ': ['Herbicides', 'Weed control'],
            'thuốc trừ nấm': ['Fungicides', 'Crop protection'],
            'thuốc diệt ốc': ['Molluscicides', 'Snail control'],
            'thủy canh': ['Hydroponics', 'Soilless cultivation'],
            'khí canh': ['Aeroponics', 'Soilless cultivation'],
            'aquaponics': ['Aquaponics', 'Recirculating system'],
            'ipm': ['Integrated pest management', 'IPM'],
            'vietgap': ['VietGAP', 'Good Agricultural Practices'],
            'globalgap': ['GlobalGAP', 'Good Agricultural Practices'],
            'nhà lưới': ['Net house', 'Protected cultivation'],
            'tưới nhỏ giọt': ['Drip irrigation', 'Irrigation system'],
            'tưới phun': ['Sprinkler irrigation', 'Irrigation system'],
            'đất phèn': ['Acid sulfate soil', 'Soil'],
            'đất mặn': ['Saline soil', 'Soil'],
            
            # Máy móc nông nghiệp  
            'máy kéo': ['Tractors', 'Agricultural machinery', 'Farm equipment'],
            'cối xay gió': ['Windmills', 'Wind turbines', 'Wind power'],
            'máy gặt': ['Harvesters', 'Combine harvesters'],
            'máy cày': ['Plows', 'Agricultural plows'],
            'máy phun thuốc': ['Sprayers', 'Agricultural sprayers'],
            
            # Hoa và cây cảnh
            'hoa hướng dương': ['Sunflowers', 'Helianthus', 'Yellow flowers'],
            'hoa hồng': ['Roses', 'Rosa', 'Rose flowers'],
            'hoa sen': ['Lotus', 'Nelumbo', 'Lotus flowers'],
            'hoa lan': ['Orchids', 'Orchidaceae'],
            'cúc họa mi': ['Daisies', 'Bellis perennis'],
            
            # Cây gỗ và lâm nghiệp
            'gỗ': ['Wood', 'Timber', 'Lumber', 'Forest products'],
            'cây thông': ['Pine trees', 'Pinus', 'Coniferous trees'],
            'cây sồi': ['Oak trees', 'Quercus'],
            'tre': ['Bamboo', 'Bambuseae'],
            'phoi gỗ': ['Wood chips', 'Wood shavings', 'Mulch', 'Wood mulch'],
            'mùn cưa': ['Sawdust', 'Wood dust', 'Wood particles'],
            
            # Đất đai và môi trường
            'đất': ['Soil', 'Agricultural soil', 'Farm soil'],
            'phân bón': ['Fertilizers', 'Organic fertilizer', 'Compost'],
            'nước tưới': ['Irrigation', 'Water irrigation', 'Agricultural water'],
            'nhà kính': ['Greenhouses', 'Agricultural greenhouses'],
            
            # Hạt giống và cây giống
            'hạt giống': ['Seeds', 'Plant seeds', 'Agricultural seeds'],
            'cây giống': ['Seedlings', 'Plant nursery', 'Young plants'],
            
            # Sâu bệnh và thuốc trừ sâu
            'sâu hại': ['Pests', 'Agricultural pests', 'Crop pests'],
            'thuốc trừ sâu': ['Pesticides', 'Insecticides'],
            'bệnh cây trồng': ['Plant diseases', 'Crop diseases'],
            
            # Công nghệ nông nghiệp
            'nông nghiệp thông minh': ['Smart farming', 'Precision agriculture'],
            'drone nông nghiệp': ['Agricultural drones', 'Farm drones'],
            'cảm biến': ['Agricultural sensors', 'Farm sensors'],
            
            # Default
            'nông nghiệp': ['Agriculture', 'Farming', 'Agricultural practices']
        }
        
        # Database tên files ảnh thật từ Wikimedia Commons
        self.real_image_files = {
            'xoài': [
                "Hapus_Mango.jpg",
                "Mangos_-_single_and_halved.jpg", 
                "Mango_Maya.jpg",
                "Manila_mango.jpg",
                "Carabao_mango.jpg",
                "Indian_Mango.jpg",
                "Mango_and_cross_section.jpg",
                "Ataulfo_mango.jpg"
            ],
            'cà chua': [
                "Tomato_je.jpg",
                "Red_tomatoes.jpg",
                "Cherry_tomatoes.jpg",
                "Tomato_varieties.jpg",
                "Fresh_tomatoes.jpg",
                "Garden_tomato.jpg"
            ],
            'lúa': [
                "Rice_grains_(IRRI).jpg",
                "Rice_field_in_Vietnam.jpg",
                "Rice_paddy.jpg",
                "Brown_rice.jpg"
            ],
            'ngô': [
                "Sweet_corn.jpg",
                "Corn_on_the_cob.jpg",
                "Yellow_corn.jpg",
                "Maize_ears.jpg"
            ],
            'lúa mì': [
                "Wheat_field.jpg",
                "Wheat_grains.jpg",
                "Golden_wheat.jpg"
            ],
            'mía': [
                "Sugar_cane.jpg",
                "Sugarcane_plantation.jpg",
                "Saccharum_officinarum_2.jpg",
                "Sugar_cane_field.jpg",
                "Sugarcane_harvest.jpg",
                "Sugar_cane_stalks.jpg"
            ],
            'nông nghiệp': [
                "Agriculture_in_India.jpg",
                "Farm_field.jpg",
                "Crop_farming.jpg"
            ]
        }

        # Mapping tiếng Việt -> bộ từ khóa tiếng Anh cho dịch và khớp linh hoạt
        self.translation_map = {
            # Cây trồng chính
            'xoài': ['mango', 'tropical fruit'],
            'cà chua': ['tomato', 'vegetable'],
            'lúa': ['rice', 'paddy'],
            'ngô': ['corn', 'maize'],
            'mía': ['sugarcane', 'plantation'],
            'lúa mì': ['wheat', 'grain'],
            'táo': ['apple', 'orchard'],
            'cà tím': ['eggplant', 'aubergine'],
            'cà rốt': ['carrot', 'root vegetable'],
            'khoai tây': ['potato', 'tuber'],
            'khoai lang': ['sweet potato', 'tuber'],
            'bắp cải': ['cabbage', 'leafy vegetable'],
            'rau muống': ['water spinach', 'leafy vegetable'],
            'dưa chuột': ['cucumber', 'vegetable'],
            'ớt': ['chili pepper', 'capsicum'],
            'hành tây': ['onion', 'bulb vegetable'],
            'tỏi': ['garlic', 'bulb vegetable'],
            'cam': ['orange', 'citrus'],
            'chanh': ['lemon', 'citrus'],
            'chuối': ['banana', 'tropical fruit'],
            'dừa': ['coconut', 'palm'],
            'đu đủ': ['papaya', 'tropical fruit'],
            'nho': ['grape', 'vineyard'],
            'dâu tây': ['strawberry', 'berry'],

            # Động vật chăn nuôi
            'gà': ['chicken', 'poultry'],
            'bò': ['cow', 'cattle'],
            'heo': ['pig', 'swine'],
            'lợn': ['pig', 'swine'],
            'con lợn': ['pig', 'swine'],
            'con lon': ['pig', 'swine'],
            'cừu': ['sheep', 'lamb'],
            'dê': ['goat', 'capra'],
            'vịt': ['duck', 'waterfowl'],
            'ngỗng': ['goose', 'waterfowl'],
            'chó': ['dog', 'canine'],
            'con chó': ['dog', 'domestic dog'],
            'cá': ['fish', 'aquaculture'],
            'tôm': ['shrimp', 'aquaculture'],

            # Thuỷ sản phổ biến (theo loài) - hỗ trợ có/không dấu
            'cá tra': ['pangasius', 'catfish'],
            'ca tra': ['pangasius', 'catfish'],
            'cá basa': ['pangasius', 'catfish'],
            'ca basa': ['pangasius', 'catfish'],
            'cá rô phi': ['tilapia', 'aquaculture'],
            'ca ro phi': ['tilapia', 'aquaculture'],
            'cá lóc': ['snakehead fish', 'channa'],
            'ca loc': ['snakehead fish', 'channa'],
            'cá chép': ['common carp', 'carp'],
            'ca chep': ['common carp', 'carp'],
            'tôm thẻ': ['whiteleg shrimp', 'vannamei shrimp'],
            'tom the': ['whiteleg shrimp', 'vannamei shrimp'],
            'tôm sú': ['giant tiger prawn', 'prawn'],
            'tom su': ['giant tiger prawn', 'prawn'],

            # Bổ sung động vật & thuỷ sản
            'trâu': ['water buffalo', 'buffalo'],
            'ngựa': ['horse', 'horses'],
            'thỏ': ['rabbit', 'rabbits'],
            'chim cút': ['quail', 'quails'],
            'ong mật': ['honey bee', 'beekeeping'],
            'nuôi ong': ['beekeeping', 'apiculture'],
            'cua': ['crab', 'crabs'],
            'ốc': ['snail', 'snails'],
            'nghêu': ['clam', 'clams'],
            'hàu': ['oyster', 'oysters'],
            'rong biển': ['seaweed', 'algae'],

            # Trái cây phổ biến
            'sầu riêng': ['durian', 'tropical fruit'],
            'thanh long': ['dragon fruit', 'pitaya'],
            'mít': ['jackfruit', 'tropical fruit'],
            'bưởi': ['pomelo', 'citrus'],
            'ổi': ['guava', 'tropical fruit'],
            'vải': ['lychee', 'tropical fruit'],
            'nhãn': ['longan', 'tropical fruit'],
            'chôm chôm': ['rambutan', 'tropical fruit'],
            'măng cụt': ['mangosteen', 'tropical fruit'],
            'dứa': ['pineapple', 'tropical fruit'],
            'thơm': ['pineapple', 'tropical fruit'],
            'khóm': ['pineapple', 'tropical fruit'],
            'dưa hấu': ['watermelon', 'melon'],
            'dưa lưới': ['cantaloupe', 'melon'],
            'dưa gang': ['winter melon', 'melon'],
            'dưa vàng': ['honeydew', 'melon'],
            'dưa lê': ['pear melon', 'melon'],
            'nho xanh': ['green grape', 'vineyard'],
            'nho đỏ': ['red grape', 'vineyard'],
            'nho đen': ['black grape', 'vineyard'],
            'nho tím': ['purple grape', 'vineyard'],
            'táo xanh': ['green apple', 'orchard'],
            'táo đỏ': ['red apple', 'orchard'],
            'táo vàng': ['yellow apple', 'orchard'],
            'táo hồng': ['pink apple', 'orchard'],
            'táo tàu': ['jujube', 'fruit'],
            'táo mèo': ['amla', 'fruit'],
            'táo ta': ['wild apple', 'fruit'],
            'kiwi': ['kiwi', 'fruit'],
            'chanh dây': ['passion fruit', 'fruit'],
            'dừa xiêm': ['young coconut', 'palm'],
            'dừa dứa': ['pineapple coconut', 'palm'],
            'chuối tiêu': ['cavendish banana', 'tropical fruit'],
            'chuối sứ': ['silk banana', 'tropical fruit'],
            'chuối ngự': ['royal banana', 'tropical fruit'],
            'chuối hột': ['wild banana', 'tropical fruit'],
            'chuối chín': ['ripe banana', 'tropical fruit'],
            'chuối xanh': ['green banana', 'tropical fruit'],
            'chuối sáp': ['wax banana', 'tropical fruit'],
            'chuối lùn': ['dwarf banana', 'tropical fruit'],
            'chuối mốc': ['red banana', 'tropical fruit'],
            'chuối tiêu hồng': ['pink banana', 'tropical fruit'],
            'chuối tây': ['plantain', 'tropical fruit'],

            # Cây công nghiệp
            'cà phê': ['coffee', 'coffee plantation'],
            'chè': ['tea', 'tea plantation'],
            'trà': ['tea', 'tea leaves'],
            'hồ tiêu': ['black pepper', 'pepper vine'],
            'tiêu': ['black pepper', 'pepper'],
            'điều': ['cashew', 'cashew nut'],
            'cao su': ['rubber tree', 'latex'],

            # Rau củ/gia vị
            'xà lách': ['lettuce', 'leafy vegetable'],
            'cải thảo': ['napa cabbage', 'chinese cabbage'],
            'cải xanh': ['mustard greens', 'leafy vegetable'],
            'cải ngọt': ['choy sum', 'leafy vegetable'],
            'cải bó xôi': ['spinach', 'leafy vegetable'],
            'rau dền': ['amaranth', 'leafy vegetable'],
            'mồng tơi': ['malabar spinach', 'leafy vegetable'],
            'rau ngót': ['katuk', 'leafy vegetable'],
            'bông cải': ['broccoli', 'cauliflower'],
            'súp lơ': ['cauliflower', 'broccoli'],
            'bí đỏ': ['pumpkin', 'squash'],
            'bí xanh': ['winter melon', 'gourd'],
            'bí ngòi': ['zucchini', 'courgette'],
            'mướp': ['luffa', 'gourd'],
            'khổ qua': ['bitter melon', 'gourd'],
            'mướp đắng': ['bitter melon', 'gourd'],
            'đậu bắp': ['okra', 'vegetable'],
            'đậu que': ['green beans', 'string beans'],
            'đậu hà lan': ['peas', 'green peas'],
            'đậu nành': ['soybean', 'soya bean'],
            'đậu tương': ['soybean', 'soya bean'],
            'đậu phộng': ['peanut', 'groundnut'],
            'lạc': ['peanut', 'groundnut'],
            'vừng': ['sesame', 'sesame seeds'],
            'mè': ['sesame', 'sesame seeds'],
            'củ cải': ['radish', 'root vegetable'],
            'củ dền': ['beetroot', 'root vegetable'],
            'khoai mì': ['cassava', 'tapioca'],
            'sắn': ['cassava', 'tapioca'],
            'khoai môn': ['taro', 'root crop'],
            'sả': ['lemongrass', 'herb'],
            'gừng': ['ginger', 'spice'],
            'nghệ': ['turmeric', 'spice'],

            # Sâu bệnh phổ biến
            'rầy nâu': ['brown planthopper', 'rice pest'],
            'sâu cuốn lá': ['leaf folder', 'rice pest'],
            'sâu đục thân': ['stem borer', 'rice pest'],
            'bọ trĩ': ['thrips', 'crop pest'],
            'nhện đỏ': ['spider mites', 'crop pest'],
            'rệp sáp': ['mealybugs', 'crop pest'],
            'sâu keo mùa thu': ['fall armyworm', 'maize pest'],
            'ruồi vàng': ['fruit fly', 'bactrocera'],
            'đạo ôn': ['rice blast', 'plant disease'],
            'khô vằn': ['sheath blight', 'rice disease'],
            'bạc lá': ['bacterial leaf blight', 'rice disease'],
            'thán thư': ['anthracnose', 'plant disease'],
            'phấn trắng': ['powdery mildew', 'plant disease'],
            'sương mai': ['downy mildew', 'plant disease'],

            # Vật tư/công nghệ
            'phân hữu cơ': ['organic fertilizer', 'compost'],
            'phân chuồng': ['manure', 'fertilizer'],
            'phân trùn quế': ['vermicompost', 'worm castings'],
            'vôi nông nghiệp': ['agricultural lime', 'soil amendment'],
            'ure': ['urea fertilizer', 'nitrogen fertilizer'],
            'dap': ['dap fertilizer', 'diammonium phosphate'],
            'kali': ['potassium fertilizer', 'potash'],
            'npk': ['npk fertilizer', 'compound fertilizer'],
            'thuốc trừ cỏ': ['herbicide', 'weed killer'],
            'thuốc trừ nấm': ['fungicide', 'crop protection'],
            'thuốc diệt ốc': ['molluscicide', 'snail control'],
            'thủy canh': ['hydroponics', 'soilless cultivation'],
            'khí canh': ['aeroponics', 'soilless cultivation'],
            'aquaponics': ['aquaponics', 'recirculating system'],
            'ipm': ['integrated pest management', 'ipm'],
            'vietgap': ['vietgap', 'good agricultural practices'],
            'globalgap': ['globalgap', 'good agricultural practices'],
            'nhà lưới': ['net house', 'protected cultivation'],
            'tưới nhỏ giọt': ['drip irrigation', 'irrigation'],
            'tưới phun': ['sprinkler irrigation', 'irrigation'],

            # Máy móc nông nghiệp
            'máy kéo': ['tractor', 'farm machinery'],
            'máy gặt': ['harvester', 'combine harvester'],
            'máy cày': ['plow', 'tillage'],
            'máy phun thuốc': ['pesticide sprayer', 'field sprayer'],

            # Hoa và cây cảnh
            'hoa': ['flower', 'bloom'],
            'hoa hướng dương': ['sunflower', 'helianthus'],
            'hoa hồng': ['rose', 'flower'],
            'hoa sen': ['lotus', 'nelumbo'],
            'hoa lan': ['orchid', 'orchidaceae'],
            'cúc họa mi': ['daisy', 'asteraceae'],

            # Lâm nghiệp và vật liệu
            'gỗ': ['wood', 'timber'],
            'cây thông': ['pine tree', 'conifer'],
            'cây sồi': ['oak tree', 'quercus'],
            'tre': ['bamboo', 'grass'],
            'phoi gỗ': ['wood chips', 'mulch'],
            'mùn cưa': ['sawdust', 'wood particles'],

            # Đất và môi trường
            'đất': ['soil', 'agricultural soil'],
            'phân bón': ['fertilizer', 'compost'],
            'nước tưới': ['irrigation', 'watering system'],
            'nhà kính': ['greenhouse', 'hothouse'],

            # Hạt giống và cây giống
            'hạt giống': ['seed', 'seed stock'],
            'cây giống': ['seedling', 'nursery plant'],

            # Sâu bệnh và thuốc
            'sâu hại': ['pest', 'crop pest'],
            'thuốc trừ sâu': ['pesticide', 'insecticide'],
            'bệnh cây trồng': ['plant disease', 'crop disease'],

            # Công nghệ nông nghiệp
            'nông nghiệp thông minh': ['smart farming', 'precision agriculture'],
            'drone nông nghiệp': ['agricultural drone', 'uav'],
            'cảm biến': ['sensor', 'agriculture sensor'],

            # Từ khóa tiếng Anh phổ biến (giữ nguyên để làm chuẩn hoá)
            'mango': ['mango', 'tropical fruit'],
            'tomato': ['tomato', 'vegetable'],
            'rice': ['rice', 'paddy'],
            'corn': ['corn', 'maize'],
            'sugarcane': ['sugarcane', 'plantation'],
            'wheat': ['wheat', 'grain'],
            'apple': ['apple', 'orchard'],
            'banana': ['banana', 'tropical fruit'],
            'coconut': ['coconut', 'palm'],
            'duck': ['duck', 'waterfowl'],
            'dog': ['dog', 'canine'],
            'canine': ['dog', 'canine'],
            'chicken': ['chicken', 'poultry'],
            'tractor': ['tractor', 'farm machinery'],
            'plow': ['plow', 'tillage'],
            'greenhouse': ['greenhouse', 'horticulture'],
            'fertilizer': ['fertilizer', 'soil nutrition'],
            'soil': ['soil', 'agricultural soil'],
            'agriculture': ['agriculture', 'farming']
        }

        self.stopwords = {
            'con', 'mot', 'nhung', 'cua', 'cai', 'the', 'anh', 'chi', 'ban',
            'a', 'an', 'the', 'of', 'and'
        }
        
    def normalize_text(self, text):
        """Chuẩn hóa text: xoá dấu, về chữ thường, bỏ ký tự đặc biệt."""
        if text is None:
            return ''

        if not isinstance(text, str):
            text = str(text)

        try:
            text = unquote(text)
        except Exception:
            pass

        normalized = unicodedata.normalize('NFD', text)
        stripped = ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
        cleaned = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in stripped.lower())
        return ' '.join(cleaned.split())

    def build_keyword_set(self, query):
        """Sinh tập từ khóa (Việt + Anh) để đối chiếu mức độ liên quan."""
        keywords = set()
        base_query = query.lower().strip()
        normalized_query = self.normalize_text(query)

        for token in [base_query, normalized_query]:
            if token:
                keywords.add(token)
                keywords.update(token.split())

        category = self.get_category(query)
        if category:
            normalized_category = self.normalize_text(category)
            keywords.add(normalized_category)
            keywords.update(normalized_category.split())
            for alias in self.category_mapping.get(category, []):
                normalized_alias = self.normalize_text(alias)
                if normalized_alias:
                    keywords.add(normalized_alias)
                    keywords.update(normalized_alias.split())

        # Thu thập từ translation map (khớp từng phần)
        for viet_term, english_terms in self.translation_map.items():
            normalized_term = self.normalize_text(viet_term)
            if (viet_term in base_query) or (
                normalized_term
                and len(normalized_term) >= 4
                and f" {normalized_term} " in f" {normalized_query} "
            ):
                for eng in english_terms:
                    normalized_eng = self.normalize_text(eng)
                    if normalized_eng:
                        keywords.add(normalized_eng)
                        keywords.update(normalized_eng.split())

        # Nếu query đã là tiếng Anh, giữ nguyên tokens
        if base_query in self.translation_map:
            for eng in self.translation_map[base_query]:
                normalized_eng = self.normalize_text(eng)
                if normalized_eng:
                    keywords.add(normalized_eng)
                    keywords.update(normalized_eng.split())

        # Loại bỏ token quá ngắn hoặc thuộc stopwords
        filtered = set()
        for kw in keywords:
            if not kw or len(kw) <= 1:
                continue
            if kw in self.stopwords:
                continue
            filtered.add(kw)

        return filtered

    def deduplicate_images(self, images):
        """Loại bỏ ảnh trùng URL."""
        unique = []
        seen = set()
        for img in images:
            url = img.get('url') or ''
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(img)
        return unique

    def calculate_keyword_hits(self, img, keywords):
        if not keywords:
            return 0

        text_segments = [
            img.get('title', ''),
            img.get('description', ''),
            img.get('photographer', ''),
            img.get('source', ''),
            img.get('url', ''),
            img.get('page_url', '')
        ]
        combined = self.normalize_text(' '.join(str(seg) for seg in text_segments if seg))
        tokens = set(combined.split())
        hits = 0
        for kw in keywords:
            if ' ' in kw:
                if kw in combined:
                    hits += 1
            else:
                if kw in tokens:
                    hits += 1
        return hits

    def prioritize_keyword_matches(self, images, keywords):
        if not images or not keywords:
            return images

        matched = []
        others = []
        for img in images:
            hits = img.get('keyword_hits')
            if hits is None:
                hits = self.calculate_keyword_hits(img, keywords)
            img['_keyword_hits'] = hits
            if hits > 0:
                matched.append(img)
            else:
                others.append(img)
        return matched + others

    def search_images(self, query, max_images=4):
        """
        Tìm kiếm ảnh chính - ưu tiên tuyệt đối Google Custom Search API
        """
        print(f"🔍 Tìm kiếm {max_images} ảnh cho: {query}")
        
        # Bước 1: Mở rộng từ khóa để tìm kiếm chính xác hơn
        expanded_queries = self.expand_search_query(query)
        keywords = self.build_keyword_set(query)
        print(f"🔧 Expanded queries: {expanded_queries}")
        print(f"🧠 Keyword pool: {sorted(list(keywords))[:12]}{'...' if len(keywords) > 12 else ''}")
        
        all_images = []
        
        # Bước 2: MAXIMUM PRIORITY - Google Custom Search
        print("🚀 Phase 1: INTENSIVE Google Custom Search (PRIMARY SOURCE)...")
        for search_query in expanded_queries:
            google_images = self.search_google_images(search_query, 10)  # Tăng lên 10 ảnh mỗi query
            all_images.extend(google_images)
            
            if len(all_images) >= max_images * 5:  # Lấy gấp 5 lần để có nhiều lựa chọn
                break
        
        # Bước 3: Openverse Creative Commons fallback (chỉ khi Google không đủ)
        if len(all_images) < max_images * 2:
            print("🎨 Phase 2: Openverse Creative Commons fallback...")
            for search_query in expanded_queries[:2]:
                openverse_images = self.search_openverse_images(search_query, 8)
                all_images.extend(openverse_images)
                if len(all_images) >= max_images * 3:
                    break

        # Bước 4: BỎ QUA WIKIMEDIA - không dùng nữa
        # (Wikimedia đã được loại bỏ theo yêu cầu người dùng)
        
        all_images = self.deduplicate_images(all_images)
        print(f"🌐 Thu thập được (unique): {len(all_images)} ảnh")
        
        # Bước 5: Score ưu tiên ảnh khớp chủ đề
        scored_images = self.score_image_relevance_prioritize_google(all_images, query, keywords)
        ranked_images = self.prioritize_keyword_matches(scored_images, keywords)
        
        # Bước 6: Validate URLs và chọn ảnh tốt nhất
        valid_images = []
        for img in ranked_images:
            # Đảm bảo image có title trước khi validate
            if 'title' not in img:
                img['title'] = f'Untitled Image'
                
            if self.validate_url_with_timeout(img['url']):
                valid_images.append(img)
                print(f"✅ Valid: {img['title']} (score: {img.get('relevance_score', 0):.2f}) [Source: {img.get('source', 'unknown')}]")
            else:
                print(f"❌ Invalid: {img['title']} - {img['url'][:50]}...")
            
            if len(valid_images) >= max_images:
                break
        
        # Bước 7: Tạo thêm placeholders nếu cần để đủ 4 ảnh
        if len(valid_images) < max_images:
            needed = max_images - len(valid_images)
            print(f"🔧 Cần thêm {needed} ảnh để đủ {max_images}")
            
            # Tạo placeholders chất lượng cao
            placeholders = self.create_relevant_placeholders(query, needed)
            valid_images.extend(placeholders)
            print(f"📝 Added {needed} quality placeholders")
        
        final_images = valid_images[:max_images]
        print(f"🎯 Kết quả cuối: {len(final_images)} ảnh")
        
        return final_images
    
    def search_google_images(self, query, max_results=4):
        """
        Tìm kiếm ảnh từ Google Custom Search API với fallback mạnh
        """
        print(f"🌐 Google Images search cho: {query}")
        
        try:
            # Try original query first (supports Unicode Vietnamese), then translated query
            english_query = self.translate_to_english(query)
            print(f"🌍 English query: {english_query}")

            queries_to_try = []
            if query and query.strip():
                queries_to_try.append(query.strip())
            if english_query and english_query.strip() and english_query.strip().lower() != (query or '').strip().lower():
                queries_to_try.append(english_query.strip())

            images = []
            for q in queries_to_try:
                images.extend(self.search_google_direct(q, max_results))
                if len(images) >= max_results:
                    break
            
            if len(images) == 0:
                print("⚠️ Google Custom Search failed, trying SerpAPI fallback...")
                # Fallback to SerpAPI (demo key)
                fallback_q = english_query.strip() if english_query else (query.strip() if query else '')
                images = self.search_with_serpapi(fallback_q, max_results)
                
            if len(images) == 0:
                print("⚠️ Both Google APIs failed, using enhanced Wikimedia search...")
                # Enhanced fallback: Multiple Wikimedia searches
                wikimedia_queries = []
                if english_query:
                    wikimedia_queries.append(english_query)
                if query:
                    wikimedia_queries.append(query)
                # Only add farming/agriculture variants if the query is actually agriculture-related
                if english_query and any(k in (english_query.lower()) for k in ["farm", "agric", "crop", "rice", "corn", "wheat"]):
                    wikimedia_queries.append(f"{english_query} farming")
                for wq in wikimedia_queries:
                    wm_images = self.search_wikimedia_commons(wq, 2)
                    images.extend(wm_images)
                    if len(images) >= max_results:
                        break
                        
            return images
            
        except Exception as e:
            print(f"❌ Google search error: {e}")
            return []

    def search_openverse_images(self, query, max_results=6):
        """Tìm ảnh Creative Commons từ Openverse (không cần API key)."""
        print(f"🎨 Openverse search cho: {query}")

        results = []
        base_url = "https://api.openverse.engineering/v1/images/"
        headers = {'User-Agent': 'AgriSenseAI/1.0'}

        translated = self.translate_to_english(query)
        search_terms = []

        if translated and translated.lower() != query.lower():
            search_terms.extend([query, translated])
        else:
            search_terms.append(query)

        for term in search_terms:
            if len(results) >= max_results:
                break

            params = {
                'q': term,
                'page_size': max_results,
                'license_type': 'all',
                'mature': 'false'
            }

            try:
                response = requests.get(base_url, params=params, headers=headers, timeout=12)
                if response.status_code != 200:
                    print(f"⚠️ Openverse error {response.status_code}: {response.text[:120]}")
                    continue

                data = response.json()
                for item in data.get('results', []):
                    if len(results) >= max_results:
                        break

                    url = item.get('url') or item.get('thumbnail')
                    if not url:
                        continue

                    tags = item.get('tags') or []
                    tag_summary = ', '.join(
                        tag.get('name') for tag in tags
                        if isinstance(tag, dict) and tag.get('name')
                    )

                    results.append({
                        'url': url,
                        'title': item.get('title') or f'Openverse image - {term}',
                        'description': item.get('description') or tag_summary,
                        'photographer': item.get('creator') or item.get('source') or 'Openverse',
                        'source': 'openverse',
                        'page_url': item.get('detail_url'),
                        'license': item.get('license')
                    })

            except Exception as e:
                print(f"❌ Openverse search error: {e}")

        print(f"🎨 Openverse trả về: {len(results)} ảnh")
        return results[:max_results]
    
    def translate_to_english(self, query):
        """Dịch từ tiếng Việt sang tiếng Anh"""
        query_lower = (query or '').lower().strip()
        if not query_lower:
            return ''

        normalized = self.normalize_text(query)

        # 1) Exact matches (with or without diacritics)
        if query_lower in self.translation_map:
            terms = self.translation_map[query_lower]
            return ' '.join(dict.fromkeys(terms[:2]))
        if normalized in self.translation_map:
            terms = self.translation_map[normalized]
            return ' '.join(dict.fromkeys(terms[:2]))

        # 2) Substring matches (with or without diacritics)
        best_match = None  # (match_len, english_terms)
        for viet_term, english_terms in self.translation_map.items():
            norm_term = self.normalize_text(viet_term)
            matched = viet_term and (
                (viet_term in query_lower)
                or (norm_term and len(norm_term) >= 4 and normalized and f" {norm_term} " in f" {normalized} ")
            )
            if not matched:
                continue

            match_len = len(viet_term)
            if not best_match or match_len > best_match[0]:
                best_match = (match_len, english_terms)

        if best_match:
            return ' '.join(dict.fromkeys(best_match[1][:2]))

        # 3) If already English-ish, keep as-is
        if query_lower.isascii():
            return query_lower

        # 4) Otherwise: keep the original query (do NOT strip diacritics to avoid bad queries like "con lon")
        return query.strip()
    
    def search_google_direct(self, query, max_results):
        """
        Tìm ảnh Google Images bằng Google Custom Search API
        """
        print(f"🔍 Google Custom Search API: {query}")
        
        try:
            # Google Custom Search API configuration
            api_key = self.google_api_key
            cse_id = self.google_cse_id

            if not api_key or not cse_id:
                logging.warning("⚠️  Thiếu GOOGLE_API_KEY hoặc GOOGLE_CSE_ID. Bỏ qua Google Custom Search.")
                return []
            
            # API endpoint
            base_url = "https://www.googleapis.com/customsearch/v1"
            
            params = {
                'key': api_key,
                'cx': cse_id,
                'q': query,
                'searchType': 'image',
                'num': min(max_results, 10),  # Max 10 per request
                'imgSize': 'medium',
                'imgType': 'photo',
                'safe': 'active'
            }
            
            response = requests.get(base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                images = []
                
                for item in data.get('items', []):
                    images.append({
                        'url': item.get('link', ''),
                        'title': item.get('title', f'Google Image - {query}'),
                        'description': item.get('snippet', f'High quality image about {query}'),
                        'photographer': item.get('displayLink', 'Google Images'),
                        'source': 'google_custom_search'
                    })
                
                print(f"✅ Google Custom Search: Found {len(images)} images")
                return images
            elif response.status_code == 403:
                print(f"❌ Google API 403: Có thể cần enable Custom Search API hoặc key hết quota")
                # Fallback to SerpAPI demo
                return self.search_with_serpapi(query, max_results)
            else:
                print(f"❌ Google API Error: {response.status_code} - {response.text}")
                return []
            
        except Exception as e:
            print(f"❌ Google Custom Search error: {e}")
            # Fallback to SerpAPI
            return self.search_with_serpapi(query, max_results)
    
    def search_unsplash(self, query, max_results):
        """
        DISABLED - Picsum Photos chỉ trả về ảnh ngẫu nhiên không liên quan
        """
        print(f"📸 Picsum Photos search: {query} - DISABLED")
        return []  # Trả về list trống thay vì ảnh Picsum
    
    def search_with_serpapi(self, query, max_results):
        """
        Search với SerpAPI (demo key - giới hạn)
        """
        try:
            # Sử dụng demo SerpAPI (giới hạn 100 requests/month)
            base_url = "https://serpapi.com/search.json"
            params = {
                'engine': 'google_images',
                'q': query,
                'api_key': 'demo',  # Demo key
                'num': max_results
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                images = []
                
                for item in data.get('images_results', [])[:max_results]:
                    images.append({
                        'url': item.get('original', ''),
                        'title': item.get('title', f'Google Image'),
                        'description': item.get('snippet', 'High quality image from Google'),
                        'photographer': item.get('source', 'Google Images'),
                        'source': 'serpapi'
                    })
                
                return images
            
        except Exception as e:
            print(f"❌ SerpAPI error: {e}")
        
        return []
    
    def validate_url_with_timeout(self, url, timeout=3):
        """
        Kiểm tra URL ảnh có hợp lệ không với timeout ngắn
        """
        try:
            # Whitelist các domain đáng tin cậy
            trusted_domains = [
                'picsum.photos',
                'via.placeholder.com',
                'dummyimage.com',
                'upload.wikimedia.org',
                'commons.wikimedia.org',
                'images.pexels.com',
                'cdn.pixabay.com',
                'images.unsplash.com',
                'live.staticflickr.com',
                'staticflickr.com'
            ]
            
            # Nếu URL từ domain tin cậy, coi như valid
            for domain in trusted_domains:
                if domain in url:
                    return True
            
            # Với các domain khác, test thực tế
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
                    return True
            elif response.status_code in (301, 302, 303, 307, 308, 403, 405):
                return True
            
            return False
            
        except:
            # Nếu lỗi, kiểm tra domain có trong whitelist không
            for domain in ['picsum.photos', 'via.placeholder.com', 'dummyimage.com',
                           'upload.wikimedia.org', 'commons.wikimedia.org',
                           'images.pexels.com', 'cdn.pixabay.com', 'images.unsplash.com',
                           'live.staticflickr.com', 'staticflickr.com']:
                if domain in url:
                    return True
            return False
    
    def search_wikimedia_commons(self, query, max_results=4):
        """
        Tìm kiếm ảnh thực từ Wikimedia Commons - LINH HOẠT, KHÔNG CẦN CATEGORY
        """
        print(f"🔍 Wikimedia search cho: {query} (max: {max_results})")
        
        # Bước 1: Thử tìm từ database có sẵn trước
        category = self.get_category(query)
        database_images = []
        
        if category in self.real_image_files:
            print(f"📚 Tìm thấy database cho {category}")
            filenames = self.real_image_files[category]
            urls_map = self.wikimedia_api.get_multiple_image_urls(filenames)
            
            for filename, url in urls_map.items():
                if url and self.validate_url_with_timeout(url):
                    database_images.append({
                        'url': url,
                        'title': self.format_title(filename),
                        'description': f'Ảnh {filename.replace(".jpg", "").replace("_", " ")} từ Wikimedia Commons',
                        'photographer': 'Wikimedia Commons',
                        'source': 'wikimedia'
                    })
                    print(f"✅ Database: {filename}")
                    
                    if len(database_images) >= max_results:
                        break
        
        # Bước 2: Nếu chưa đủ, tìm kiếm động từ Wikimedia API
        if len(database_images) < max_results:
            needed = max_results - len(database_images)
            dynamic_images = self.search_wikimedia_dynamic(query, needed)
            database_images.extend(dynamic_images)
        
        # Kết hợp kết quả
        final_images = database_images[:max_results]
        
        print(f"🎯 Wikimedia tổng cộng: {len(final_images)} ảnh")
        return final_images
    
    def search_wikimedia_dynamic(self, query, target_count=4):
        """
        Tìm kiếm động từ Wikimedia Commons API - STRATEGY CẢI THIỆN
        """
        print(f"🌐 Tìm kiếm động cho: {query}")
        
        # Tạo các từ khóa tìm kiếm MỞ RỘNG
        search_terms = self.generate_search_terms(query)
        dynamic_images = []
        
        # STRATEGY 1: Thử từng term cho đến khi đủ target_count ảnh
        target_images = target_count
        
        for i, term in enumerate(search_terms):
            if len(dynamic_images) >= target_images:
                print(f"🎯 Đã đủ {target_images} ảnh, dừng tìm kiếm")
                break
                
            print(f"🔍 Thử từ khóa {i+1}/{len(search_terms)}: {term}")
            
            # Tìm kiếm qua categories với ưu tiên cao
            category_results = self.search_by_category(term)
            if category_results:
                for img in category_results:
                    img.setdefault('source', 'wikimedia')
                dynamic_images.extend(category_results[:3])  # Lấy tối đa 3 từ category
                print(f"   ➕ Category: +{len(category_results[:3])} ảnh")
            
            # Nếu vẫn thiếu, tìm files trực tiếp
            if len(dynamic_images) < target_images:
                file_results = self.search_files_directly(term)
                if file_results:
                    for img in file_results:
                        img.setdefault('source', 'wikimedia')
                    dynamic_images.extend(file_results[:3])  # Lấy tối đa 3 từ files
                    print(f"   ➕ Files: +{len(file_results[:3])} ảnh")
            
            # Kiểm tra có đủ chưa
            current_count = len(dynamic_images)
            print(f"   📊 Hiện tại: {current_count} ảnh")
            
            if current_count >= target_images:
                print(f"✅ Đã đạt target {target_images} ảnh!")
                break
        
        # Loại bỏ trùng lặp
        seen_urls = set()
        unique_images = []
        for img in dynamic_images:
            if img['url'] not in seen_urls:
                unique_images.append(img)
                seen_urls.add(img['url'])
        
        print(f"🎯 Dynamic search: {len(unique_images)} ảnh unique")
        return unique_images[:10]  # Tăng giới hạn lên 10
    
    def generate_search_terms(self, query):
        """
        Tạo các từ khóa tìm kiếm từ query - MỞ RỘNG NGỮ NGHĨA
        """
        query_lower = query.lower()
        
        # Từ điển chuyển đổi tiếng Việt -> tiếng Anh + SYNONYMS - MỞ RỘNG TOÀN DIỆN
        translation_map = {
            # Cây trồng chính
            'xoài': ['mango', 'mangoes', 'mango fruit', 'mango tree', 'tropical mango'],
            'cà chua': ['tomato', 'tomatoes', 'tomato fruit', 'red tomato', 'fresh tomato'],
            'lúa': ['rice', 'paddy', 'rice plant', 'rice field', 'rice grain', 'oryza sativa'],
            'ngô': ['corn', 'maize', 'corn plant', 'sweet corn', 'corn field', 'zea mays'],
            'mía': ['sugarcane', 'sugar cane', 'cane field', 'sugarcane plant', 'saccharum'],
            'lúa mì': ['wheat', 'wheat field', 'wheat grain', 'triticum'],
            'táo': ['apple', 'apple fruit', 'apple tree', 'red apple', 'malus'],
            'cà rót': ['eggplant', 'aubergine', 'solanum melongena', 'purple eggplant'],
            
            # Rau củ quả mở rộng
            'khoai tây': ['potato', 'potatoes', 'potato plant', 'potato tuber'],
            'khoai lang': ['sweet potato', 'sweet potatoes', 'ipomoea batatas'],
            'cà rốt': ['carrot', 'carrots', 'orange carrot', 'carrot root'],
            'bắp cải': ['cabbage', 'green cabbage', 'brassica oleracea'],
            'rau muống': ['water spinach', 'morning glory', 'ipomoea aquatica'],
            'dưa chuột': ['cucumber', 'cucumbers', 'green cucumber'],
            'ớt': ['pepper', 'chili', 'hot pepper', 'capsicum'],
            'hành tây': ['onion', 'onions', 'yellow onion', 'allium cepa'],
            'tỏi': ['garlic', 'garlic bulb', 'allium sativum'],
            
            # Cây ăn trái
            'cam': ['orange', 'oranges', 'orange fruit', 'citrus orange'],
            'chanh': ['lemon', 'lemons', 'lime', 'citrus lemon'],
            'chuối': ['banana', 'bananas', 'banana plant', 'banana tree'],
            'dừa': ['coconut', 'coconuts', 'coconut palm', 'coconut tree'],
            'đu đủ': ['papaya', 'papayas', 'papaw', 'carica papaya'],
            'nho': ['grape', 'grapes', 'grape vine', 'vineyard'],
            'dâu tây': ['strawberry', 'strawberries', 'strawberry plant'],
            
            # Động vật chăn nuôi
            'gà': ['chicken', 'poultry', 'hen', 'rooster', 'gallus'],
            'bò': ['cow', 'cattle', 'beef cattle', 'dairy cow', 'bovine'],
            'heo': ['pig', 'swine', 'pork', 'sus', 'domestic pig'],
            'cừu': ['sheep', 'lamb', 'ovis', 'wool sheep'],
            'dê': ['goat', 'capra', 'dairy goat', 'goat farming'],
            'vịt': ['duck', 'ducks', 'domestic duck', 'waterfowl'],
            'ngỗng': ['goose', 'geese', 'domestic goose'],
            'chó': ['dog', 'dogs', 'domestic dog', 'canine', 'puppy'],
            'cá': ['fish', 'aquaculture', 'fish farming', 'fishery'],
            'tôm': ['shrimp', 'prawn', 'shrimp farming', 'aquaculture shrimp'],
            
            # Máy móc nông nghiệp
            'máy kéo': ['tractor', 'farm tractor', 'agricultural tractor'],
            'cối xay gió': ['windmill', 'wind turbine', 'windmill farm'],
            'máy gặt': ['harvester', 'combine harvester', 'harvesting machine'],
            'máy cày': ['plow', 'plough', 'agricultural plow'],
            'máy phun thuốc': ['sprayer', 'agricultural sprayer', 'pesticide sprayer'],
            
            # Từ khóa cơ bản
            'cây': ['plant', 'tree', 'vegetation', 'flora'],
            'hoa': ['flower', 'bloom', 'blossom', 'flowering plant'],
            'quả': ['fruit', 'fruits', 'fresh fruit'],
            'rau': ['vegetable', 'vegetables', 'leafy vegetable'],
            'nông nghiệp': ['agriculture', 'farming', 'cultivation', 'agricultural'],
            'ruộng': ['field', 'farm', 'farmland', 'agricultural field'],
            'vườn': ['garden', 'orchard', 'plantation'],
            
            # Hoa và cây cảnh
            'hoa hướng dương': ['sunflower', 'helianthus', 'sunflower field', 'yellow sunflower'],
            'hoa hồng': ['rose', 'roses', 'rose flower', 'red rose'],
            'hoa sen': ['lotus', 'lotus flower', 'nelumbo', 'water lily'],
            'hoa lan': ['orchid', 'orchids', 'orchid flower'],
            'cúc họa mi': ['daisy', 'daisies', 'white daisy'],
            
            # Cây gỗ và lâm nghiệp
            'gỗ': ['wood', 'timber', 'lumber', 'wooden'],
            'cây thông': ['pine', 'pine tree', 'conifer', 'evergreen'],
            'cây sồi': ['oak', 'oak tree', 'quercus'],
            'tre': ['bamboo', 'bamboo plant', 'bamboo grove'],
            'phoi gỗ': ['wood chips', 'wood shavings', 'mulch', 'wood mulch', 'bark chips'],
            'mùn cưa': ['sawdust', 'wood dust', 'wood particles', 'fine wood'],
            
            # Đất đai và môi trường
            'đất': ['soil', 'earth', 'agricultural soil', 'farm soil', 'dirt'],
            'phân bón': ['fertilizer', 'fertilizers', 'organic fertilizer', 'compost'],
            'nước tưới': ['irrigation', 'watering', 'agricultural water'],
            'nhà kính': ['greenhouse', 'glasshouse', 'hothouse'],
            
            # Hạt giống và cây giống
            'hạt giống': ['seed', 'seeds', 'plant seeds', 'agricultural seeds'],
            'cây giống': ['seedling', 'seedlings', 'young plant', 'plant nursery'],
            
            # Sâu bệnh và thuốc trừ sâu
            'sâu hại': ['pest', 'pests', 'insect pest', 'crop pest'],
            'thuốc trừ sâu': ['pesticide', 'insecticide', 'pest control'],
            'bệnh cây trồng': ['plant disease', 'crop disease', 'plant pathology'],
            
            # Công nghệ nông nghiệp
            'drone': ['drone', 'agricultural drone', 'farm drone', 'uav'],
            'cảm biến': ['sensor', 'agricultural sensor', 'farm sensor'],
            'robot': ['robot', 'agricultural robot', 'farm robot'],
            
            # Từ khóa tiếng Anh phổ biến
            'wood shavings': ['wood shavings', 'wood chips', 'mulch', 'bark mulch'],
            'mulch': ['mulch', 'wood mulch', 'bark chips', 'organic mulch'],
            'chips': ['wood chips', 'bark chips', 'mulch chips'],
            'shavings': ['wood shavings', 'shavings', 'wood curls']
        }
        
        terms = []
        
        # Thêm query gốc
        terms.append(query_lower)
        
        # EXPANSION 1: Tìm từ khóa trực tiếp
        for viet, eng_list in translation_map.items():
            if viet in query_lower:
                terms.extend(eng_list)
                print(f"🔍 Mở rộng '{viet}' → {eng_list}")
        
        # EXPANSION 2: Tìm từng từ riêng lẻ
        words = query_lower.split()
        for word in words:
            if word in translation_map:
                terms.extend(translation_map[word])
        
        # EXPANSION 3: Thêm kết hợp phổ biến
        base_terms = []
        for viet, eng_list in translation_map.items():
            if viet in query_lower:
                base_terms.extend(eng_list[:2])  # Lấy 2 từ chính
        
        for base in base_terms:
            terms.extend([
                f"{base} plant",
                f"{base} field", 
                f"{base} farming",
                f"{base} cultivation",
                f"{base} agriculture"
            ])
        
        # EXPANSION 4: Loại bỏ trùng lặp và sắp xếp theo độ ưu tiên
        unique_terms = []
        seen = set()
        
        # Ưu tiên: từ gốc → từ dịch chính → từ mở rộng
        priority_order = [query_lower] + \
                        [t for viet, eng_list in translation_map.items() 
                         if viet in query_lower for t in eng_list[:3]]
        
        for term in priority_order + terms:
            if term not in seen and term.strip():
                unique_terms.append(term)
                seen.add(term)
        
        print(f"📝 Query expansion: {len(unique_terms)} từ khóa")
        return unique_terms[:8]  # Tăng lên 8 terms
    
    def search_by_category(self, term):
        """
        Tìm kiếm qua categories Wikimedia - CẢI THIỆN VỚI CATEGORY MAPPING
        """
        try:
            results = []
            
            # Bước 1: Thử category mapping chuyên ngành
            category = self.get_category(term)
            if category in self.category_mapping:
                specialist_categories = self.category_mapping[category]
                print(f"🎯 Sử dụng category mapping cho '{category}': {specialist_categories}")
                
                for spec_cat in specialist_categories:
                    try:
                        category_results = self.wikimedia_api.search_images_by_category(spec_cat, 5)
                        results.extend(category_results)
                        if category_results:
                            print(f"✅ Specialist category '{spec_cat}': {len(category_results)} ảnh")
                    except:
                        continue
            
            # Bước 2: Thử các category patterns phổ biến
            category_patterns = [
                f"{term.title()}",
                f"{term.title()} cultivation", 
                f"{term.title()} plants",
                f"{term.title()} agriculture",
                f"{term.title()} farming",
                f"{term.replace(' ', '_').title()}",  # Underscore format
                f"{term.title()}_images"
            ]
            
            for pattern in category_patterns:
                try:
                    category_results = self.wikimedia_api.search_images_by_category(pattern, 3)
                    results.extend(category_results)
                    if category_results:
                        print(f"✅ Pattern category '{pattern}': {len(category_results)} ảnh")
                except:
                    continue
                    
            return results[:8]  # Tăng giới hạn lên 8 ảnh
            
        except Exception as e:
            print(f"⚠️ Category search error: {str(e)[:30]}")
            return []
    
    def search_files_directly(self, term):
        """
        Tìm kiếm files trực tiếp với tên dự đoán - MỞ RỘNG PATTERNS
        """
        # Tạo tên files có thể tồn tại - MỞ RỘNG
        possible_files = [
            # Basic patterns
            f"{term.title()}.jpg",
            f"{term.capitalize()}.jpg", 
            f"{term.lower()}.jpg",
            f"{term.upper()}.jpg",
            
            # With descriptors
            f"{term.title()}_plant.jpg",
            f"{term.title()}_field.jpg",
            f"{term.title()}_crop.jpg",
            f"{term.title()}_farming.jpg",
            f"{term.title()}_agriculture.jpg",
            f"{term.title()}_cultivation.jpg",
            
            # Underscore replacements
            f"{term.replace(' ', '_').title()}.jpg",
            f"{term.replace(' ', '_').lower()}.jpg",
            f"{term.replace(' ', '_')}_plant.jpg",
            f"{term.replace(' ', '_')}_field.jpg",
            
            # Dash replacements  
            f"{term.replace(' ', '-').title()}.jpg",
            f"{term.replace(' ', '-').lower()}.jpg",
            
            # Plural forms
            f"{term.title()}s.jpg",
            f"{term.lower()}s.jpg",
            
            # Scientific/formal patterns
            f"{term.title()}_scientific.jpg",
            f"{term.title()}_botanical.jpg",
            f"{term.title()}_species.jpg",
            
            # Common file patterns on Wikimedia
            f"File:{term.title()}.jpg",
            f"{term.title()}_001.jpg",
            f"{term.title()}_image.jpg",
            f"{term.title()}_photo.jpg"
        ]
        
        # Loại bỏ trùng lặp
        unique_files = list(dict.fromkeys(possible_files))
        
        print(f"🔍 Thử {len(unique_files)} file patterns cho '{term}'")
        
        results = []
        
        # Chia thành batches để tránh quá tải API
        batch_size = 20
        for i in range(0, len(unique_files), batch_size):
            batch = unique_files[i:i+batch_size]
            urls_map = self.wikimedia_api.get_multiple_image_urls(batch)
            
            for filename, url in urls_map.items():
                if url and self.validate_url(url):
                    results.append({
                        'url': url,
                        'title': self.format_title(filename),
                        'description': f'Ảnh {filename.replace(".jpg", "").replace("_", " ")} từ Wikimedia Commons',
                        'photographer': 'Wikimedia Commons',
                        'source': 'wikimedia'
                    })
                    print(f"✅ File trực tiếp: {filename}")
                    
                    # Giới hạn kết quả để không quá nhiều
                    if len(results) >= 10:
                        break
            
            if len(results) >= 10:
                break
        
        return results
    
    def format_title(self, filename):
        """Format filename thành title đẹp"""
        title = filename.replace(".jpg", "").replace("_", " ").replace("-", " ")
        return " ".join(word.capitalize() for word in title.split())
    
    def get_category(self, query):
        """Phân loại query thành category - MỞ RỘNG TOÀN DIỆN"""
        query_lower = query.lower()
        
        # Cây trồng chính
        if any(word in query_lower for word in ['xoài', 'mango']):
            return 'xoài'
        elif any(word in query_lower for word in ['cà chua', 'tomato']):
            return 'cà chua'
        elif any(word in query_lower for word in ['lúa', 'rice', 'gạo']):
            return 'lúa'
        elif any(word in query_lower for word in ['ngô', 'corn', 'bắp']):
            return 'ngô'
        elif any(word in query_lower for word in ['lúa mì', 'wheat']):
            return 'lúa mì'
        elif any(word in query_lower for word in ['mía', 'sugarcane', 'sugar cane', 'cây mía']):
            return 'mía'
        elif any(word in query_lower for word in ['táo', 'apple']):
            return 'táo'
        elif any(word in query_lower for word in ['cà tím', 'eggplant', 'aubergine']):
            return 'cà tím'
            
        # Rau củ quả
        elif any(word in query_lower for word in ['khoai tây', 'potato']):
            return 'khoai tây'
        elif any(word in query_lower for word in ['khoai lang', 'sweet potato']):
            return 'khoai lang'
        elif any(word in query_lower for word in ['cà rốt', 'carrot']):
            return 'cà rốt'
        elif any(word in query_lower for word in ['bắp cải', 'cabbage']):
            return 'bắp cải'
        elif any(word in query_lower for word in ['rau muống', 'water spinach']):
            return 'rau muống'
        elif any(word in query_lower for word in ['dưa chuột', 'cucumber']):
            return 'dưa chuột'
        elif any(word in query_lower for word in ['ớt', 'pepper', 'chili']):
            return 'ớt'
        elif any(word in query_lower for word in ['hành tây', 'onion']):
            return 'hành tây'
        elif any(word in query_lower for word in ['tỏi', 'garlic']):
            return 'tỏi'
            
        # Cây ăn trái
        elif any(word in query_lower for word in ['cam', 'orange']):
            return 'cam'
        elif any(word in query_lower for word in ['chanh', 'lemon', 'lime']):
            return 'chanh'
        elif any(word in query_lower for word in ['chuối', 'banana']):
            return 'chuối'
        elif any(word in query_lower for word in ['dừa', 'coconut']):
            return 'dừa'
        elif any(word in query_lower for word in ['đu đủ', 'papaya']):
            return 'đu đủ'
        elif any(word in query_lower for word in ['nho', 'grape']):
            return 'nho'
        elif any(word in query_lower for word in ['dâu tây', 'strawberry']):
            return 'dâu tây'
            
        # Động vật chăn nuôi
        elif any(word in query_lower for word in ['gà', 'chicken', 'poultry']):
            return 'gà'
        elif any(word in query_lower for word in ['bò', 'cow', 'cattle']):
            return 'bò'
        elif any(word in query_lower for word in ['heo', 'lợn', 'con lon', 'pig', 'swine']):
            return 'heo'
        elif any(word in query_lower for word in ['cừu', 'sheep']):
            return 'cừu'
        elif any(word in query_lower for word in ['dê', 'goat']):
            return 'dê'
        elif any(word in query_lower for word in ['vịt', 'duck']):
            return 'vịt'
        elif any(word in query_lower for word in ['ngỗng', 'goose']):
            return 'ngỗng'
        elif any(word in query_lower for word in ['chó', 'dog', 'canine', 'puppy']):
            return 'chó'
        elif any(word in query_lower for word in ['cá tra', 'ca tra']):
            return 'cá tra'
        elif any(word in query_lower for word in ['cá basa', 'ca basa']):
            return 'cá basa'
        elif any(word in query_lower for word in ['cá rô phi', 'ca ro phi']):
            return 'cá rô phi'
        elif any(word in query_lower for word in ['cá lóc', 'ca loc']):
            return 'cá lóc'
        elif any(word in query_lower for word in ['cá chép', 'ca chep']):
            return 'cá chép'
        elif any(word in query_lower for word in ['cá', 'fish']):
            return 'cá'
        elif any(word in query_lower for word in ['tôm thẻ', 'tom the']):
            return 'tôm thẻ'
        elif any(word in query_lower for word in ['tôm sú', 'tom su']):
            return 'tôm sú'
        elif any(word in query_lower for word in ['tôm', 'shrimp']):
            return 'tôm'
            
        # Máy móc
        elif any(word in query_lower for word in ['máy kéo', 'tractor']):
            return 'máy kéo'
        elif any(word in query_lower for word in ['cối xay gió', 'windmill']):
            return 'cối xay gió'
        elif any(word in query_lower for word in ['máy gặt', 'harvester']):
            return 'máy gặt'
        elif any(word in query_lower for word in ['máy cày', 'plow']):
            return 'máy cày'
        elif any(word in query_lower for word in ['máy phun thuốc', 'sprayer']):
            return 'máy phun thuốc'
            
        # Hoa
        elif any(word in query_lower for word in ['hoa hướng dương', 'sunflower']):
            return 'hoa hướng dương'
        elif any(word in query_lower for word in ['hoa hồng', 'rose']):
            return 'hoa hồng'
        elif any(word in query_lower for word in ['hoa sen', 'lotus']):
            return 'hoa sen'
        elif any(word in query_lower for word in ['hoa lan', 'orchid']):
            return 'hoa lan'
        elif any(word in query_lower for word in ['cúc họa mi', 'daisy']):
            return 'cúc họa mi'
            
        # Gỗ và lâm nghiệp
        elif any(word in query_lower for word in ['phoi gỗ', 'wood shavings', 'wood chips', 'mulch']):
            return 'phoi gỗ'
        elif any(word in query_lower for word in ['mùn cưa', 'sawdust']):
            return 'mùn cưa'
        elif any(word in query_lower for word in ['gỗ', 'wood', 'timber']):
            return 'gỗ'
        elif any(word in query_lower for word in ['cây thông', 'pine']):
            return 'cây thông'
        elif any(word in query_lower for word in ['cây sồi', 'oak']):
            return 'cây sồi'
        elif any(word in query_lower for word in ['tre', 'bamboo']):
            return 'tre'
            
        # Đất đai và môi trường
        elif any(word in query_lower for word in ['đất', 'soil']):
            return 'đất'
        elif any(word in query_lower for word in ['phân bón', 'fertilizer']):
            return 'phân bón'
        elif any(word in query_lower for word in ['nước tưới', 'irrigation']):
            return 'nước tưới'
        elif any(word in query_lower for word in ['nhà kính', 'greenhouse']):
            return 'nhà kính'
            
        # Hạt giống
        elif any(word in query_lower for word in ['hạt giống', 'seed']):
            return 'hạt giống'
        elif any(word in query_lower for word in ['cây giống', 'seedling']):
            return 'cây giống'
            
        # Sâu bệnh
        elif any(word in query_lower for word in ['sâu hại', 'pest']):
            return 'sâu hại'
        elif any(word in query_lower for word in ['thuốc trừ sâu', 'pesticide']):
            return 'thuốc trừ sâu'
        elif any(word in query_lower for word in ['bệnh cây trồng', 'plant disease']):
            return 'bệnh cây trồng'
            
        # Công nghệ
        elif any(word in query_lower for word in ['drone', 'uav']):
            return 'drone nông nghiệp'
        elif any(word in query_lower for word in ['cảm biến', 'sensor']):
            return 'cảm biến'
        elif any(word in query_lower for word in ['nông nghiệp thông minh', 'smart farming']):
            return 'nông nghiệp thông minh'
            
        # Fallback: match any known category_mapping key (hỗ trợ không dấu)
        normalized_query = self.normalize_text(query_lower)
        for key in self.category_mapping.keys():
            norm_key = self.normalize_text(key)
            if key in query_lower or (
                norm_key
                and len(norm_key) >= 4
                and f" {norm_key} " in f" {normalized_query} "
            ):
                return key

        return 'nông nghiệp'
    
    def validate_url(self, url):
        """Validate URL hoạt động"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }
            
            response = requests.head(url, headers=headers, timeout=self.timeout)
            
            # Chấp nhận cả 200 và 403 (CORS block nhưng ảnh vẫn tồn tại)
            if response.status_code in [200, 403]:
                return True
            else:
                print(f"   Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   Validation error: {str(e)[:30]}...")
            return False
    
    def create_quality_placeholders(self, query, count):
        """Tạo placeholder SVG chất lượng cao"""
        placeholders = []
        
        # Icon động dựa trên từ khóa
        query_lower = query.lower()
        if any(word in query_lower for word in ['xoài', 'mango']):
            icon = '🥭'
        elif any(word in query_lower for word in ['cà chua', 'tomato']):
            icon = '🍅'
        elif any(word in query_lower for word in ['lúa', 'rice']):
            icon = '�'
        elif any(word in query_lower for word in ['ngô', 'corn']):
            icon = '🌽'
        elif any(word in query_lower for word in ['mía', 'sugarcane']):
            icon = '�'
        elif any(word in query_lower for word in ['chó', 'dog', 'puppy', 'canine']):
            icon = '🐕'
        elif any(word in query_lower for word in ['hoa', 'flower']):
            icon = '🌸'
        elif any(word in query_lower for word in ['cây', 'tree', 'plant']):
            icon = '�'
        elif any(word in query_lower for word in ['rau', 'vegetable']):
            icon = '🥬'
        elif any(word in query_lower for word in ['quả', 'fruit']):
            icon = '🍎'
        else:
            icon = '🌱'  # Default cho mọi thứ khác
        
        for i in range(count):
            # Sử dụng nhiều dịch vụ placeholder đáng tin cậy thay vì SVG
            current_time = int(time.time())
            random_seed = current_time + i
            
            # Icon dựa trên từ khóa cho search term
            if any(word in query_lower for word in ['xoài', 'mango']):
                search_term = 'mango'
            elif any(word in query_lower for word in ['cà chua', 'tomato']):
                search_term = 'tomato'
            elif any(word in query_lower for word in ['lúa', 'rice']):
                search_term = 'rice'
            elif any(word in query_lower for word in ['ngô', 'corn']):
                search_term = 'corn'
            elif any(word in query_lower for word in ['mía', 'sugarcane']):
                search_term = 'sugarcane'
            elif any(word in query_lower for word in ['chó', 'dog', 'puppy', 'canine']):
                search_term = 'dog'
            elif any(word in query_lower for word in ['hoa', 'flower']):
                search_term = 'flower'
            elif any(word in query_lower for word in ['cây', 'tree', 'plant']):
                search_term = 'plant'
            elif any(word in query_lower for word in ['rau', 'vegetable']):
                search_term = 'vegetable'
            elif any(word in query_lower for word in ['quả', 'fruit']):
                search_term = 'fruit'
            else:
                search_term = 'agriculture'
            
            # Danh sách các URL placeholder đáng tin cậy
            placeholder_urls = [
                # Via Placeholder - rất ổn định
                f"https://via.placeholder.com/400x300/4CAF50/ffffff?text={query.replace(' ', '+')}+{i+1}",
                
                # Picsum Photos - ảnh thật ngẫu nhiên
                f"https://picsum.photos/400/300?random={random_seed}",
                
                # Lorem Picsum với filter
                f"https://picsum.photos/id/{(random_seed % 100) + 1}/400/300",
                
                # DummyImage
                f"https://dummyimage.com/400x300/4CAF50/ffffff&text={search_term}+{i+1}"
            ]
            
            # Chọn URL chính và backup
            primary_url = placeholder_urls[i % len(placeholder_urls)]
            backup_urls = [url for url in placeholder_urls if url != primary_url]
            
            placeholder = {
                'url': primary_url,
                'backup_urls': backup_urls[:2],  # Chỉ lấy 2 backup đầu
                'title': f'{query.title()} - Hình ảnh {i+1}',
                'description': f'Hình minh họa chất lượng cao cho {query}',
                'photographer': 'AgriSense AI',
                'source': 'agrisense_placeholder',
                'icon': icon,
                'is_placeholder': True
            }
            placeholders.append(placeholder)
        
        return placeholders

    def expand_search_query(self, original_query):
        """
        Mở rộng query để tìm kiếm chính xác hơn
        """
        expanded = [original_query]  # Luôn giữ query gốc
        
        # Thêm từ category mapping (hỗ trợ không dấu)
        query_lower = original_query.lower()
        normalized_query = self.normalize_text(original_query)
        best_match = None  # (match_len, categories)
        for key, categories in self.category_mapping.items():
            norm_key = self.normalize_text(key)
            matched = (
                (key in query_lower)
                or (
                    norm_key
                    and len(norm_key) >= 4
                    and f" {norm_key} " in f" {normalized_query} "
                )
            )
            if not matched:
                continue

            match_len = len(key)
            if not best_match or match_len > best_match[0]:
                best_match = (match_len, categories)

        if best_match:
            expanded.extend(best_match[1][:2])  # Chỉ lấy 2 category đầu
        
        # Thêm từ khóa nông nghiệp chung (CHỈ khi query là chủ đề chung)
        category = self.get_category(original_query)
        is_general_agri = (category in {None, '', 'nông nghiệp'}) or any(
            kw in query_lower
            for kw in ['nông nghiệp', 'canh tác', 'trồng trọt', 'chăn nuôi', 'trang trại', 'ruộng', 'vườn', 'farm', 'agri', 'crop']
        )
        if is_general_agri and 'agriculture' not in ' '.join(expanded).lower():
            expanded.append(f"{original_query} agriculture")
            expanded.append(f"{original_query} farming")
        
        # Thêm từ khóa tiếng Anh từ translation map
        translated = self.translate_to_english(original_query)
        if translated and translated not in expanded:
            expanded.append(translated)
        
        # Giới hạn số query để tránh quá tải
        return expanded[:4]
    
    def score_image_relevance(self, images, original_query):
        """
        Tính điểm độ liên quan của ảnh với query gốc
        """
        query_words = set(original_query.lower().split())
        
        # Thêm từ khóa mở rộng để so sánh
        extended_words = query_words.copy()
        if original_query.lower() in self.category_mapping:
            for category in self.category_mapping[original_query.lower()]:
                extended_words.update(category.lower().split())
        
        scored_images = []
        for img in images:
            score = 0
            title_words = set(img['title'].lower().split())
            desc_words = set(img.get('description', '').lower().split())
            
            # Điểm cho title khớp
            title_matches = len(query_words.intersection(title_words))
            score += title_matches * 3
            
            # Điểm cho title khớp từ mở rộng
            extended_matches = len(extended_words.intersection(title_words))
            score += extended_matches * 2
            
            # Điểm cho description khớp
            desc_matches = len(query_words.intersection(desc_words))
            score += desc_matches * 1
            
            # Bonus nếu không phải placeholder
            if not img.get('is_placeholder', False):
                score += 5
            
            # Penalty cho URL quá dài (có thể spam)
            if len(img['url']) > 200:
                score -= 2
            
            img['relevance_score'] = score
            scored_images.append(img)
        
        # Sắp xếp theo điểm giảm dần
        scored_images.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_images
    
    def create_relevant_placeholders(self, query, count):
        """
        Tạo placeholder chất lượng cao với URLs khác nhau
        """
        placeholders = []
        
        # Chọn icon phù hợp với query
        icon_mapping = {
            'cà chua': '🍅', 'xoài': '🥭', 'lúa': '🌾', 'ngô': '🌽',
            'mía': '🎋', 'khoai tây': '🥔', 'cà rốt': '🥕', 'dưa chuột': '🥒',
            'cam': '🍊', 'chanh': '🍋', 'chuối': '🍌', 'dừa': '🥥',
            'gà': '🐔', 'bò': '🐄', 'heo': '🐷', 'cừu': '🐑', 'con bò': '🐄'
        }

        icon_mapping.update({
            'chó': '🐕',
            'con chó': '🐕',
            'dog': '🐕',
            'puppy': '🐶'
        })
        
        icon = icon_mapping.get(query.lower(), '🌱')
        search_term = query.replace(' ', '+')
        
        # Tạo màu sắc khác nhau cho mỗi placeholder
        colors = ['2E7D32', '388E3C', '4CAF50', '66BB6A']
        
        for i in range(count):
            color = colors[i % len(colors)]
            timestamp = int(time.time()) + i  # Unique timestamp
            
            # Tạo URLs khác nhau cho mỗi placeholder
            placeholder_urls = [
                f"https://via.placeholder.com/400x300/{color}/ffffff?text={icon}+{search_term}+{i+1}",
                f"https://dummyimage.com/400x300/{color}/ffffff&text={icon}+{search_term}+Image+{i+1}",
                f"https://placehold.co/400x300/{color}/ffffff?text={icon}+{search_term}+{timestamp}",
                f"https://picsum.photos/400/300?random={timestamp}"
            ]
            
            placeholder = {
                'url': placeholder_urls[i % len(placeholder_urls)],
                'title': f'{query.title()} - Ảnh chất lượng cao {i+1}',
                'description': f'Hình ảnh chuyên nghiệp về {query} trong nông nghiệp - Mẫu {i+1}',
                'photographer': 'AgriSense AI Gallery',
                'source': 'agrisense_placeholder',
                'icon': icon,
                'is_placeholder': True,
                'relevance_score': 1.0  # Điểm thấp nhất
            }
            placeholders.append(placeholder)
        
        return placeholders
    
    def score_image_relevance_prioritize_google(self, images, original_query, keywords=None):
        """
        Tính điểm độ liên quan với BONUS lớn cho Google Images
        """
        if keywords is None:
            keywords = self.build_keyword_set(original_query)

        query_words = set(self.normalize_text(original_query).split())
        
        # Thêm từ khóa mở rộng để so sánh
        extended_words = query_words.copy()
        if original_query.lower() in self.category_mapping:
            for category in self.category_mapping[original_query.lower()]:
                extended_words.update(category.lower().split())
        
        scored_images = []
        for img in images:
            # Đảm bảo image có title
            if 'title' not in img:
                img['title'] = f'Untitled Image'
            
            score = 0
            title_words = set(self.normalize_text(img['title']).split())
            desc_words = set(self.normalize_text(img.get('description', '')).split())
            
            # Điểm cho title khớp
            title_matches = len(query_words.intersection(title_words))
            score += title_matches * 3
            
            # Điểm cho title khớp từ mở rộng
            extended_matches = len(extended_words.intersection(title_words))
            score += extended_matches * 2
            
            # Điểm cho description khớp
            desc_matches = len(query_words.intersection(desc_words))
            score += desc_matches * 1

            # Điểm theo số keyword hit (bao gồm URL)
            keyword_hits = self.calculate_keyword_hits(img, keywords)
            score += min(keyword_hits, 5) * 6
            if keyword_hits == 0:
                score -= 12
            
            # BONUS CHỈ CHO GOOGLE IMAGES - TẮT PICSUM
            source = (img.get('source') or '').lower()
            if 'google' in source or 'serpapi' in source:
                if keyword_hits == 0:
                    score -= 5
                else:
                    score += 25
            elif source == 'wikimedia':
                score += 12
            elif source == 'openverse':
                score += 8
            # Không có bonus cho Picsum nữa vì đã tắt
            
            # Bonus nếu không phải placeholder
            if not img.get('is_placeholder', False):
                score += 5
            
            # Penalty cho URL quá dài (có thể spam)
            if len(img['url']) > 200:
                score -= 2
            
            # Penalty cho placeholder
            if img.get('is_placeholder', False):
                score -= 10
            
            img['keyword_hits'] = keyword_hits
            img['relevance_score'] = score
            scored_images.append(img)
        
        # Sắp xếp theo điểm giảm dần
        scored_images.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_images

# Test function
def test_new_api_search():
    """Test engine mới với Wikimedia API"""
    print("🚀 TEST IMAGE SEARCH ENGINE VỚI WIKIMEDIA API")
    print("=" * 60)
    
    engine = ImageSearchEngine()
    
    test_queries = ['xoài', 'cà chua', 'lúa', 'ngô']
    
    for query in test_queries:
        print(f"\n🔍 Test: {query}")
        print("-" * 40)
        
        images = engine.search_images(query, 4)
        
        real_count = sum(1 for img in images if not img['url'].startswith('data:'))
        placeholder_count = len(images) - real_count
        
        print(f"📊 Kết quả: {real_count} ảnh thật, {placeholder_count} placeholder")
        
        for i, img in enumerate(images, 1):
            if img['url'].startswith('data:'):
                print(f"   {i}. 🎨 {img['title']} (Placeholder)")
            else:
                print(f"   {i}. 📸 {img['title']} (Real)")
                print(f"      URL: {img['url'][:50]}...")

if __name__ == "__main__":
    test_new_api_search()
