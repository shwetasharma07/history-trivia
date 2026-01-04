QUESTIONS = [
    # ANCIENT HISTORY
    {
        "id": 1,
        "era": "ancient",
        "question": "What famous structure did the ancient Egyptians build as tombs for their pharaohs?",
        "choices": ["Castles", "Pyramids", "Igloos", "Treehouses"],
        "correct": 1,
        "fun_fact": "The Great Pyramid of Giza was the tallest building in the world for over 3,800 years!"
    },
    {
        "id": 2,
        "era": "ancient",
        "question": "Which animal was considered sacred in ancient Egypt?",
        "choices": ["Dogs", "Pigs", "Cats", "Elephants"],
        "correct": 2,
        "fun_fact": "Ancient Egyptians loved cats so much that when a family cat died, the family would shave their eyebrows in mourning!"
    },
    {
        "id": 3,
        "era": "ancient",
        "question": "What did ancient Romans use to brush their teeth?",
        "choices": ["Toothbrushes", "Crushed bones and shells", "Candy", "Nothing at all"],
        "correct": 1,
        "fun_fact": "Romans also used urine as mouthwash because it contains ammonia, which is a cleaning agent!"
    },
    {
        "id": 4,
        "era": "ancient",
        "question": "In ancient Greece, what sporting event brought all wars to a stop?",
        "choices": ["The Super Bowl", "The Olympic Games", "The World Cup", "The Dance Competition"],
        "correct": 1,
        "fun_fact": "The ancient Olympics lasted for 5 days and athletes competed completely naked!"
    },
    {
        "id": 5,
        "era": "ancient",
        "question": "What material did ancient Egyptians use to write on?",
        "choices": ["Paper", "Papyrus", "Plastic", "Leaves"],
        "correct": 1,
        "fun_fact": "Papyrus was made from a plant that grew along the Nile River. The word 'paper' comes from 'papyrus'!"
    },

    # MEDIEVAL HISTORY
    {
        "id": 6,
        "era": "medieval",
        "question": "What did knights wear to protect themselves in battle?",
        "choices": ["Pajamas", "Armor", "Swimsuits", "Blankets"],
        "correct": 1,
        "fun_fact": "A full suit of armor could weigh between 45-55 pounds - about as heavy as a large dog!"
    },
    {
        "id": 7,
        "era": "medieval",
        "question": "What were Viking ships called?",
        "choices": ["Submarines", "Longships", "Canoes", "Rockets"],
        "correct": 1,
        "fun_fact": "Viking longships were so well-designed that they could sail in just 3 feet of water!"
    },
    {
        "id": 8,
        "era": "medieval",
        "question": "What was a castle's deep ditch filled with water called?",
        "choices": ["Swimming pool", "Bathtub", "Moat", "Pond"],
        "correct": 2,
        "fun_fact": "Most moats weren't filled with crocodiles like in movies - they were often just really smelly because people threw garbage in them!"
    },
    {
        "id": 9,
        "era": "medieval",
        "question": "What disease spread across Europe in the 1300s and was called the 'Black Death'?",
        "choices": ["The common cold", "The Bubonic Plague", "Chickenpox", "Hiccups"],
        "correct": 1,
        "fun_fact": "People thought the plague was spread by bad smells, so doctors wore masks filled with flowers and herbs!"
    },
    {
        "id": 10,
        "era": "medieval",
        "question": "What weapon did Robin Hood famously use?",
        "choices": ["A sword", "A bow and arrow", "A magic wand", "A slingshot"],
        "correct": 1,
        "fun_fact": "In medieval England, all men were required by law to practice archery on Sundays!"
    },

    # MODERN HISTORY
    {
        "id": 11,
        "era": "modern",
        "question": "Who was the first person to walk on the moon?",
        "choices": ["Buzz Lightyear", "Neil Armstrong", "Albert Einstein", "Mickey Mouse"],
        "correct": 1,
        "fun_fact": "Neil Armstrong's footprints are still on the moon because there's no wind to blow them away!"
    },
    {
        "id": 12,
        "era": "modern",
        "question": "What ship sank in 1912 after hitting an iceberg?",
        "choices": ["The Mayflower", "The Titanic", "Noah's Ark", "The Pirate Ship"],
        "correct": 1,
        "fun_fact": "The Titanic had a swimming pool, a gym, and even a squash court on board!"
    },
    {
        "id": 13,
        "era": "modern",
        "question": "Who gave the famous 'I Have a Dream' speech?",
        "choices": ["Abraham Lincoln", "Martin Luther King Jr.", "George Washington", "SpongeBob"],
        "correct": 1,
        "fun_fact": "The 'I Have a Dream' part was actually improvised - it wasn't in his written speech!"
    },
    {
        "id": 14,
        "era": "modern",
        "question": "What toy was invented in 1958 and became a huge craze?",
        "choices": ["Video games", "The Hula Hoop", "Smartphones", "Teddy bears"],
        "correct": 1,
        "fun_fact": "In the first year, over 100 million Hula Hoops were sold!"
    },
    {
        "id": 15,
        "era": "modern",
        "question": "What wall came down in Germany in 1989?",
        "choices": ["The Great Wall", "The Berlin Wall", "A garden wall", "The bathroom wall"],
        "correct": 1,
        "fun_fact": "People celebrated by chipping off pieces of the wall as souvenirs. You can still buy pieces today!"
    },
    {
        "id": 16,
        "era": "modern",
        "question": "Who invented the telephone?",
        "choices": ["Alexander Graham Bell", "Thomas Edison", "Steve Jobs", "Benjamin Franklin"],
        "correct": 0,
        "fun_fact": "The first words ever spoken on a telephone were 'Mr. Watson, come here, I want to see you!'"
    },
    {
        "id": 17,
        "era": "ancient",
        "question": "What wonder of the ancient world was a giant statue in Greece?",
        "choices": ["The Colossus of Rhodes", "The Statue of Liberty", "Big Ben", "The Leaning Tower"],
        "correct": 0,
        "fun_fact": "The Colossus of Rhodes was about 100 feet tall - roughly the same height as the Statue of Liberty!"
    },
    {
        "id": 18,
        "era": "medieval",
        "question": "What did jesters do in medieval castles?",
        "choices": ["Cook food", "Entertain and make jokes", "Fight battles", "Clean the floors"],
        "correct": 1,
        "fun_fact": "Jesters were the only people allowed to make fun of the king without getting in trouble!"
    },
]


def get_questions_by_era(era: str = None):
    if era:
        return [q for q in QUESTIONS if q["era"] == era]
    return QUESTIONS


def get_random_questions(count: int = 10):
    import random
    questions = QUESTIONS.copy()
    random.shuffle(questions)
    return questions[:count]
