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
        ]
    },
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
        ]
    },
    "our_people": {
        "translations": {"en": "Our People", "es": "Nuestra Gente"},
        "words": [
            {"key": "miguel", "en": "Miguel", "es": "Miguel"},
            {"key": "matias", "en": "Matías", "es": "Matías"},
            {"key": "mateo", "en": "Mateo", "es": "Mateo"},
            {"key": "fali", "en": "Fali", "es": "Fali"},
            {"key": "jamele", "en": "Jamele", "es": "Jamele"},
            {"key": "cristobal", "en": "Cristóbal", "es": "Cristóbal"},
            {"key": "christian", "en": "Christian", "es": "Christian"},
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
