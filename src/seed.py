"""
Seed script to populate the database with sample data.

This script creates sample categories and words with translations in multiple languages.
Run this script to populate the database for testing purposes.
"""

import asyncio

from sqlalchemy import select, text

from src.categories.models import Category, CategoryTranslation
from src.database import async_session_maker, init_db
from src.words.models import Word, WordTranslation


# ========== SEED DATA ==========

CATEGORIES_DATA = {
    "football_players": {
        "translations": {"en": "Football Players", "es": "Jugadores de Fútbol"},
        "words": [
            {"key": "messi", "en": "Messi", "es": "Messi"},
            {"key": "cristiano_ronaldo", "en": "Cristiano Ronaldo", "es": "Cristiano Ronaldo"},
            {"key": "mbappe", "en": "Mbappé", "es": "Mbappé"},
            {"key": "neymar", "en": "Neymar", "es": "Neymar"},
            {"key": "haaland", "en": "Haaland", "es": "Haaland"},
            {"key": "vinicius", "en": "Vinicius Jr", "es": "Vinicius Jr"},
            {"key": "bellingham", "en": "Bellingham", "es": "Bellingham"},
            {"key": "de_bruyne", "en": "De Bruyne", "es": "De Bruyne"},
            {"key": "modric", "en": "Modric", "es": "Modric"},
            {"key": "lewandowski", "en": "Lewandowski", "es": "Lewandowski"},
            {"key": "salah", "en": "Salah", "es": "Salah"},
            {"key": "benzema", "en": "Benzema", "es": "Benzema"},
            {"key": "harry_kane", "en": "Harry Kane", "es": "Harry Kane"},
            {"key": "pedri", "en": "Pedri", "es": "Pedri"},
            {"key": "gavi", "en": "Gavi", "es": "Gavi"},
            {"key": "courtois", "en": "Courtois", "es": "Courtois"},
            {"key": "ter_stegen", "en": "Ter Stegen", "es": "Ter Stegen"},
            {"key": "sergio_ramos", "en": "Sergio Ramos", "es": "Sergio Ramos"},
            {"key": "griezmann", "en": "Griezmann", "es": "Griezmann"},
            {"key": "son", "en": "Son Heung-min", "es": "Son Heung-min"},
        ]
    },
    "tv_series": {
        "translations": {"en": "TV Series", "es": "Series de TV"},
        "words": [
            {"key": "breaking_bad", "en": "Breaking Bad", "es": "Breaking Bad"},
            {"key": "game_of_thrones", "en": "Game of Thrones", "es": "Juego de Tronos"},
            {"key": "stranger_things", "en": "Stranger Things", "es": "Stranger Things"},
            {"key": "the_office", "en": "The Office", "es": "The Office"},
            {"key": "friends", "en": "Friends", "es": "Friends"},
            {"key": "squid_game", "en": "Squid Game", "es": "El Juego del Calamar"},
            {"key": "la_casa_de_papel", "en": "Money Heist", "es": "La Casa de Papel"},
            {"key": "the_witcher", "en": "The Witcher", "es": "The Witcher"},
            {"key": "peaky_blinders", "en": "Peaky Blinders", "es": "Peaky Blinders"},
            {"key": "wednesday", "en": "Wednesday", "es": "Miércoles"},
            {"key": "the_mandalorian", "en": "The Mandalorian", "es": "The Mandalorian"},
            {"key": "euphoria", "en": "Euphoria", "es": "Euphoria"},
            {"key": "the_boys", "en": "The Boys", "es": "The Boys"},
            {"key": "black_mirror", "en": "Black Mirror", "es": "Black Mirror"},
            {"key": "the_crown", "en": "The Crown", "es": "The Crown"},
            {"key": "the_last_of_us", "en": "The Last of Us", "es": "The Last of Us"},
            {"key": "succession", "en": "Succession", "es": "Succession"},
            {"key": "better_call_saul", "en": "Better Call Saul", "es": "Better Call Saul"},
            {"key": "dark", "en": "Dark", "es": "Dark"},
            {"key": "arcane", "en": "Arcane", "es": "Arcane"},
        ]
    },
    "movies": {
        "translations": {"en": "Movies", "es": "Películas"},
        "words": [
            {"key": "avengers", "en": "Avengers", "es": "Los Vengadores"},
            {"key": "titanic", "en": "Titanic", "es": "Titanic"},
            {"key": "avatar", "en": "Avatar", "es": "Avatar"},
            {"key": "star_wars", "en": "Star Wars", "es": "Star Wars"},
            {"key": "harry_potter", "en": "Harry Potter", "es": "Harry Potter"},
            {"key": "the_godfather", "en": "The Godfather", "es": "El Padrino"},
            {"key": "jurassic_park", "en": "Jurassic Park", "es": "Jurassic Park"},
            {"key": "batman", "en": "Batman", "es": "Batman"},
            {"key": "spiderman", "en": "Spider-Man", "es": "Spider-Man"},
            {"key": "fast_and_furious", "en": "Fast & Furious", "es": "Rápidos y Furiosos"},
            {"key": "john_wick", "en": "John Wick", "es": "John Wick"},
            {"key": "interstellar", "en": "Interstellar", "es": "Interstellar"},
            {"key": "inception", "en": "Inception", "es": "Origen"},
            {"key": "the_matrix", "en": "The Matrix", "es": "Matrix"},
            {"key": "lord_of_the_rings", "en": "Lord of the Rings", "es": "El Señor de los Anillos"},
            {"key": "pulp_fiction", "en": "Pulp Fiction", "es": "Pulp Fiction"},
            {"key": "fight_club", "en": "Fight Club", "es": "El Club de la Lucha"},
            {"key": "forrest_gump", "en": "Forrest Gump", "es": "Forrest Gump"},
            {"key": "the_lion_king", "en": "The Lion King", "es": "El Rey León"},
            {"key": "joker", "en": "Joker", "es": "Joker"},
        ]
    },
    "pokemons": {
        "translations": {"en": "Pokemon", "es": "Pokémon"},
        "words": [
            {"key": "pikachu", "en": "Pikachu", "es": "Pikachu"},
            {"key": "charizard", "en": "Charizard", "es": "Charizard"},
            {"key": "bulbasaur", "en": "Bulbasaur", "es": "Bulbasaur"},
            {"key": "squirtle", "en": "Squirtle", "es": "Squirtle"},
            {"key": "jigglypuff", "en": "Jigglypuff", "es": "Jigglypuff"},
            {"key": "meowth", "en": "Meowth", "es": "Meowth"},
            {"key": "psyduck", "en": "Psyduck", "es": "Psyduck"},
            {"key": "snorlax", "en": "Snorlax", "es": "Snorlax"},
            {"key": "mewtwo", "en": "Mewtwo", "es": "Mewtwo"},
            {"key": "mew", "en": "Mew", "es": "Mew"},
            {"key": "eevee", "en": "Eevee", "es": "Eevee"},
            {"key": "gengar", "en": "Gengar", "es": "Gengar"},
            {"key": "lucario", "en": "Lucario", "es": "Lucario"},
            {"key": "greninja", "en": "Greninja", "es": "Greninja"},
            {"key": "rayquaza", "en": "Rayquaza", "es": "Rayquaza"},
            {"key": "lugia", "en": "Lugia", "es": "Lugia"},
            {"key": "gyarados", "en": "Gyarados", "es": "Gyarados"},
            {"key": "dragonite", "en": "Dragonite", "es": "Dragonite"},
            {"key": "gardevoir", "en": "Gardevoir", "es": "Gardevoir"},
            {"key": "arceus", "en": "Arceus", "es": "Arceus"},
        ]
    },
    "anime": {
        "translations": {"en": "Anime", "es": "Anime"},
        "words": [
            {"key": "naruto", "en": "Naruto", "es": "Naruto"},
            {"key": "goku", "en": "Goku", "es": "Goku"},
            {"key": "luffy", "en": "Luffy", "es": "Luffy"},
            {"key": "eren_yeager", "en": "Eren Yeager", "es": "Eren Yeager"},
            {"key": "light_yagami", "en": "Light Yagami", "es": "Light Yagami"},
            {"key": "saitama", "en": "Saitama", "es": "Saitama"},
            {"key": "lelouch", "en": "Lelouch", "es": "Lelouch"},
            {"key": "itachi", "en": "Itachi", "es": "Itachi"},
            {"key": "zoro", "en": "Zoro", "es": "Zoro"},
            {"key": "vegeta", "en": "Vegeta", "es": "Vegeta"},
            {"key": "levi_ackerman", "en": "Levi Ackerman", "es": "Levi Ackerman"},
            {"key": "tanjiro", "en": "Tanjiro", "es": "Tanjiro"},
            {"key": "deku", "en": "Deku", "es": "Deku"},
            {"key": "gojo", "en": "Gojo Satoru", "es": "Gojo Satoru"},
            {"key": "edward_elric", "en": "Edward Elric", "es": "Edward Elric"},
            {"key": "spike", "en": "Spike Spiegel", "es": "Spike Spiegel"},
            {"key": "ichigo", "en": "Ichigo", "es": "Ichigo"},
            {"key": "gon", "en": "Gon Freecss", "es": "Gon Freecss"},
            {"key": "killua", "en": "Killua", "es": "Killua"},
            {"key": "sailor_moon", "en": "Sailor Moon", "es": "Sailor Moon"},
        ]
    },
    "animals": {
        "translations": {"en": "Animals", "es": "Animales"},
        "words": [
            {"key": "dog", "en": "Dog", "es": "Perro"},
            {"key": "cat", "en": "Cat", "es": "Gato"},
            {"key": "lion", "en": "Lion", "es": "León"},
            {"key": "elephant", "en": "Elephant", "es": "Elefante"},
            {"key": "dolphin", "en": "Dolphin", "es": "Delfín"},
            {"key": "eagle", "en": "Eagle", "es": "Águila"},
            {"key": "shark", "en": "Shark", "es": "Tiburón"},
            {"key": "tiger", "en": "Tiger", "es": "Tigre"},
            {"key": "monkey", "en": "Monkey", "es": "Mono"},
            {"key": "penguin", "en": "Penguin", "es": "Pingüino"},
            {"key": "wolf", "en": "Wolf", "es": "Lobo"},
            {"key": "horse", "en": "Horse", "es": "Caballo"},
            {"key": "bear", "en": "Bear", "es": "Oso"},
            {"key": "giraffe", "en": "Giraffe", "es": "Jirafa"},
            {"key": "zebra", "en": "Zebra", "es": "Cebra"},
            {"key": "kangaroo", "en": "Kangaroo", "es": "Canguro"},
            {"key": "panda", "en": "Panda", "es": "Panda"},
            {"key": "snake", "en": "Snake", "es": "Serpiente"},
            {"key": "crocodile", "en": "Crocodile", "es": "Cocodrilo"},
            {"key": "rabbit", "en": "Rabbit", "es": "Conejo"},
        ]
    },
    "food": {
        "translations": {"en": "Food", "es": "Comida"},
        "words": [
            {"key": "pizza", "en": "Pizza", "es": "Pizza"},
            {"key": "hamburger", "en": "Hamburger", "es": "Hamburguesa"},
            {"key": "sushi", "en": "Sushi", "es": "Sushi"},
            {"key": "tacos", "en": "Tacos", "es": "Tacos"},
            {"key": "paella", "en": "Paella", "es": "Paella"},
            {"key": "pasta", "en": "Pasta", "es": "Pasta"},
            {"key": "ramen", "en": "Ramen", "es": "Ramen"},
            {"key": "croissant", "en": "Croissant", "es": "Croissant"},
            {"key": "kebab", "en": "Kebab", "es": "Kebab"},
            {"key": "tortilla", "en": "Spanish Omelette", "es": "Tortilla Española"},
            {"key": "nachos", "en": "Nachos", "es": "Nachos"},
            {"key": "churros", "en": "Churros", "es": "Churros"},
            {"key": "ice_cream", "en": "Ice Cream", "es": "Helado"},
            {"key": "chocolate", "en": "Chocolate", "es": "Chocolate"},
            {"key": "steak", "en": "Steak", "es": "Filete"},
            {"key": "salad", "en": "Salad", "es": "Ensalada"},
            {"key": "soup", "en": "Soup", "es": "Sopa"},
            {"key": "curry", "en": "Curry", "es": "Curry"},
            {"key": "burrito", "en": "Burrito", "es": "Burrito"},
            {"key": "hot_dog", "en": "Hot Dog", "es": "Perrito Caliente"},
        ]
    },
    "house_of_twins": {
        "translations": {"en": "House of Twins", "es": "Casa de los Gemelos"},
        "words": [
            {"key": "falete", "en": "Falete", "es": "Falete"},
            {"key": "la_marrash", "en": "La Marrash", "es": "La Marrash"},
            {"key": "misha", "en": "Misha", "es": "Misha"},
            {"key": "patica", "en": "Patica", "es": "Patica"},
        ]
    },
    "cities": {
        "translations": {"en": "Cities", "es": "Ciudades"},
        "words": [
            {"key": "new_york", "en": "New York", "es": "Nueva York"},
            {"key": "london", "en": "London", "es": "Londres"},
            {"key": "paris", "en": "Paris", "es": "París"},
            {"key": "tokyo", "en": "Tokyo", "es": "Tokio"},
            {"key": "madrid", "en": "Madrid", "es": "Madrid"},
            {"key": "barcelona", "en": "Barcelona", "es": "Barcelona"},
            {"key": "rome", "en": "Rome", "es": "Roma"},
            {"key": "berlin", "en": "Berlin", "es": "Berlín"},
            {"key": "dubai", "en": "Dubai", "es": "Dubái"},
            {"key": "sydney", "en": "Sydney", "es": "Sídney"},
            {"key": "rio", "en": "Rio de Janeiro", "es": "Río de Janeiro"},
            {"key": "buenos_aires", "en": "Buenos Aires", "es": "Buenos Aires"},
            {"key": "mexico_city", "en": "Mexico City", "es": "Ciudad de México"},
            {"key": "los_angeles", "en": "Los Angeles", "es": "Los Ángeles"},
            {"key": "chicago", "en": "Chicago", "es": "Chicago"},
            {"key": "toronto", "en": "Toronto", "es": "Toronto"},
            {"key": "moscow", "en": "Moscow", "es": "Moscú"},
            {"key": "istanbul", "en": "Istanbul", "es": "Estambul"},
            {"key": "bangkok", "en": "Bangkok", "es": "Bangkok"},
            {"key": "seoul", "en": "Seoul", "es": "Seúl"},
        ]
    },
    "uyuyuyuy_fc": {
        "translations": {"en": "UyUyUyUy FC", "es": "UyUyUyUy FC"},
        "words": [
            {"key": "matias", "en": "Matías", "es": "Matías"},
            {"key": "miguel", "en": "Miguel", "es": "Miguel"},
            {"key": "melendez", "en": "Melendez", "es": "Melendez"},
            {"key": "cristobal", "en": "Cristóbal", "es": "Cristóbal"},
            {"key": "fali", "en": "Fali", "es": "Fali"},
            {"key": "christian", "en": "Christian", "es": "Christian"},
        ]
    },
    "monuments": {
        "translations": {"en": "Monuments", "es": "Monumentos"},
        "words": [
            {"key": "eiffel_tower", "en": "Eiffel Tower", "es": "Torre Eiffel"},
            {"key": "statue_of_liberty", "en": "Statue of Liberty", "es": "Estatua de la Libertad"},
            {"key": "great_wall", "en": "Great Wall of China", "es": "Gran Muralla China"},
            {"key": "taj_mahal", "en": "Taj Mahal", "es": "Taj Mahal"},
            {"key": "colosseum", "en": "Colosseum", "es": "Coliseo"},
            {"key": "machu_picchu", "en": "Machu Picchu", "es": "Machu Picchu"},
            {"key": "christ_redeemer", "en": "Christ the Redeemer", "es": "Cristo Redentor"},
            {"key": "pyramids", "en": "Pyramids of Giza", "es": "Pirámides de Giza"},
            {"key": "big_ben", "en": "Big Ben", "es": "Big Ben"},
            {"key": "sydney_opera", "en": "Sydney Opera House", "es": "Ópera de Sídney"},
            {"key": "sagrada_familia", "en": "Sagrada Familia", "es": "Sagrada Familia"},
            {"key": "petra", "en": "Petra", "es": "Petra"},
            {"key": "stonehenge", "en": "Stonehenge", "es": "Stonehenge"},
            {"key": "burj_khalifa", "en": "Burj Khalifa", "es": "Burj Khalifa"},
            {"key": "golden_gate", "en": "Golden Gate Bridge", "es": "Golden Gate"},
            {"key": "louvre", "en": "Louvre Museum", "es": "Museo del Louvre"},
            {"key": "acropolis", "en": "Acropolis", "es": "Acrópolis"},
            {"key": "mount_rushmore", "en": "Mount Rushmore", "es": "Monte Rushmore"},
            {"key": "alhambra", "en": "Alhambra", "es": "Alhambra"},
            {"key": "chichen_itza", "en": "Chichen Itza", "es": "Chichén Itzá"},
        ]
    },
    "professions": {
        "translations": {"en": "Professions", "es": "Profesiones"},
        "words": [
            {"key": "doctor", "en": "Doctor", "es": "Médico"},
            {"key": "teacher", "en": "Teacher", "es": "Profesor"},
            {"key": "engineer", "en": "Engineer", "es": "Ingeniero"},
            {"key": "lawyer", "en": "Lawyer", "es": "Abogado"},
            {"key": "police", "en": "Police Officer", "es": "Policía"},
            {"key": "firefighter", "en": "Firefighter", "es": "Bombero"},
            {"key": "chef", "en": "Chef", "es": "Cocinero"},
            {"key": "artist", "en": "Artist", "es": "Artista"},
            {"key": "musician", "en": "Musician", "es": "Músico"},
            {"key": "actor", "en": "Actor", "es": "Actor"},
            {"key": "pilot", "en": "Pilot", "es": "Piloto"},
            {"key": "astronaut", "en": "Astronaut", "es": "Astronauta"},
            {"key": "scientist", "en": "Scientist", "es": "Científico"},
            {"key": "nurse", "en": "Nurse", "es": "Enfermero"},
            {"key": "architect", "en": "Architect", "es": "Arquitecto"},
            {"key": "writer", "en": "Writer", "es": "Escritor"},
            {"key": "photographer", "en": "Photographer", "es": "Fotógrafo"},
            {"key": "farmer", "en": "Farmer", "es": "Granjero"},
            {"key": "carpenter", "en": "Carpenter", "es": "Carpintero"},
            {"key": "electrician", "en": "Electrician", "es": "Electricista"},
        ]
    },
    "videogames": {
        "translations": {"en": "Video Games", "es": "Videojuegos"},
        "words": [
            {"key": "minecraft", "en": "Minecraft", "es": "Minecraft"},
            {"key": "fortnite", "en": "Fortnite", "es": "Fortnite"},
            {"key": "gta_v", "en": "GTA V", "es": "GTA V"},
            {"key": "league_of_legends", "en": "League of Legends", "es": "League of Legends"},
            {"key": "valorant", "en": "Valorant", "es": "Valorant"},
            {"key": "call_of_duty", "en": "Call of Duty", "es": "Call of Duty"},
            {"key": "fifa", "en": "FIFA / EA FC", "es": "FIFA / EA FC"},
            {"key": "zelda", "en": "Zelda", "es": "Zelda"},
            {"key": "god_of_war", "en": "God of War", "es": "God of War"},
            {"key": "elden_ring", "en": "Elden Ring", "es": "Elden Ring"},
            {"key": "roblox", "en": "Roblox", "es": "Roblox"},
            {"key": "among_us", "en": "Among Us", "es": "Among Us"},
            {"key": "mario", "en": "Super Mario", "es": "Super Mario"},
            {"key": "pokemon_game", "en": "Pokemon", "es": "Pokemon"},
            {"key": "overwatch", "en": "Overwatch", "es": "Overwatch"},
            {"key": "csgo", "en": "Counter-Strike", "es": "Counter-Strike"},
            {"key": "sims", "en": "The Sims", "es": "Los Sims"},
            {"key": "rdr2", "en": "Red Dead Redemption", "es": "Red Dead Redemption"},
            {"key": "cyberpunk", "en": "Cyberpunk 2077", "es": "Cyberpunk 2077"},
            {"key": "rocket_league", "en": "Rocket League", "es": "Rocket League"},
        ]
    },
    "brands": {
        "translations": {"en": "Brands", "es": "Marcas"},
        "words": [
            {"key": "nike", "en": "Nike", "es": "Nike"},
            {"key": "adidas", "en": "Adidas", "es": "Adidas"},
            {"key": "gucci", "en": "Gucci", "es": "Gucci"},
            {"key": "louis_vuitton", "en": "Louis Vuitton", "es": "Louis Vuitton"},
            {"key": "zara", "en": "Zara", "es": "Zara"},
            {"key": "supreme", "en": "Supreme", "es": "Supreme"},
            {"key": "balenciaga", "en": "Balenciaga", "es": "Balenciaga"},
            {"key": "prada", "en": "Prada", "es": "Prada"},
            {"key": "versace", "en": "Versace", "es": "Versace"},
            {"key": "apple", "en": "Apple", "es": "Apple"},
            {"key": "samsung", "en": "Samsung", "es": "Samsung"},
            {"key": "coca_cola", "en": "Coca-Cola", "es": "Coca-Cola"},
            {"key": "pepsi", "en": "Pepsi", "es": "Pepsi"},
            {"key": "mcdonalds", "en": "McDonald's", "es": "McDonald's"},
            {"key": "burger_king", "en": "Burger King", "es": "Burger King"},
            {"key": "tesla", "en": "Tesla", "es": "Tesla"},
            {"key": "amazon", "en": "Amazon", "es": "Amazon"},
            {"key": "google", "en": "Google", "es": "Google"},
            {"key": "microsoft", "en": "Microsoft", "es": "Microsoft"},
            {"key": "disney", "en": "Disney", "es": "Disney"},
        ]
    },
    "celebrities": {
        "translations": {"en": "Celebrities", "es": "Famosos"},
        "words": [
            {"key": "elon_musk", "en": "Elon Musk", "es": "Elon Musk"},
            {"key": "taylor_swift", "en": "Taylor Swift", "es": "Taylor Swift"},
            {"key": "bad_bunny", "en": "Bad Bunny", "es": "Bad Bunny"},
            {"key": "the_rock", "en": "The Rock", "es": "La Roca"},
            {"key": "kim_kardashian", "en": "Kim Kardashian", "es": "Kim Kardashian"},
            {"key": "shakira", "en": "Shakira", "es": "Shakira"},
            {"key": "drake", "en": "Drake", "es": "Drake"},
            {"key": "billie_eilish", "en": "Billie Eilish", "es": "Billie Eilish"},
            {"key": "mr_beast", "en": "MrBeast", "es": "MrBeast"},
            {"key": "ibai", "en": "Ibai Llanos", "es": "Ibai Llanos"},
            {"key": "rosalia", "en": "Rosalía", "es": "Rosalía"},
            {"key": "auronplay", "en": "AuronPlay", "es": "AuronPlay"},
            {"key": "beyonce", "en": "Beyoncé", "es": "Beyoncé"},
            {"key": "rihanna", "en": "Rihanna", "es": "Rihanna"},
            {"key": "justin_bieber", "en": "Justin Bieber", "es": "Justin Bieber"},
            {"key": "ariana_grande", "en": "Ariana Grande", "es": "Ariana Grande"},
            {"key": "will_smith", "en": "Will Smith", "es": "Will Smith"},
            {"key": "tom_cruise", "en": "Tom Cruise", "es": "Tom Cruise"},
            {"key": "messi_celeb", "en": "Lionel Messi", "es": "Lionel Messi"},
            {"key": "ronaldo_celeb", "en": "Cristiano Ronaldo", "es": "Cristiano Ronaldo"},
        ]
    },
}


async def clear_database():
    """Clear all data from the database."""
    
    print("🗑️  Clearing database...")
    
    await init_db()
    
    async with async_session_maker() as session:
        # Delete in correct order to respect foreign keys
        await session.execute(text("DELETE FROM word_translation"))
        await session.execute(text("DELETE FROM word"))
        await session.execute(text("DELETE FROM category_translation"))
        await session.execute(text("DELETE FROM category"))
        await session.commit()
    
    print("✅ Database cleared!")


async def seed_database():
    """Seed the database with sample data."""
    
    # Initialize database tables
    print("🔧 Initializing database...")
    await init_db()
    
    # Clear existing data first
    await clear_database()
    
    async with async_session_maker() as session:
        print("🌱 Seeding database with sample data...")
        
        total_categories = 0
        total_words = 0
        
        for category_key, category_data in CATEGORIES_DATA.items():
            # Create category
            category = Category(key=category_key)
            session.add(category)
            await session.flush()
            
            # Add category translations
            for lang, name in category_data["translations"].items():
                session.add(CategoryTranslation(
                    category_id=category.id,
                    language=lang,
                    name=name
                ))
            
            total_categories += 1
            
            # Add words for this category
            for word_data in category_data["words"]:
                word = Word(key=word_data["key"], category_id=category.id)
                session.add(word)
                await session.flush()
                
                # Add word translations
                session.add(WordTranslation(
                    word_id=word.id,
                    language="en",
                    value=word_data["en"]
                ))
                session.add(WordTranslation(
                    word_id=word.id,
                    language="es",
                    value=word_data["es"]
                ))
                
                total_words += 1
            
            print(f"   ✓ {category_data['translations']['es']}: {len(category_data['words'])} palabras")
        
        await session.commit()
        
        print("\n✅ Database seeded successfully!")
        print(f"\n📊 Summary:")
        print(f"   - {total_categories} categories created")
        print(f"   - {total_words} words created")
        print(f"   - Translations in: English, Spanish")
        print(f"\n🚀 You can now test the API at http://localhost:8000/docs")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database())


async def seed_if_empty():
    """Seed the database only if it's empty (no categories exist)."""
    async with async_session_maker() as session:
        result = await session.execute(select(Category).limit(1))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("📦 Database already has data, skipping seed.")
            return False
    
    print("🌱 Database is empty, running seed...")
    await seed_database()
    return True
