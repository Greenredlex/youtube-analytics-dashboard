import os 
API_KEY =  os.getenv('API') # get from env
CHANNEL_IDS = [
    "UCMiJRAwDNSNzuYeN2uWa0pA",  # Mrwhosetheboss
    "UCBJycsmduvYEL83R_U4JriQ",  # Marques Brownlee
    "UCXuqSBlHAE6Xw-yeJA0Tunw",  # Linus Tech Tips
    "UCWFKCr40YwOZQx8FHU_ZqqQ",  # JerryRigEverything
    "UCXGgrKt94gR6lmN4aN3mYTg",  # Austin Evans
    "UCsTcErHg8oDvUnTzoqsYeNw",  # Unbox Therapy
]
CHANNEL_COLORS = {
    "Mrwhosetheboss": "#800000",
    "Marques Brownlee": "#008000",
    "Linus Tech Tips": "#000080",
    "JerryRigEverything": "#808000",
    "Austin Evans": "#800080",
    "Unbox Therapy": "#008080",
}
CSV_FILE_PATH = "data/videos.csv"
UPDATE_INTERVAL = 60  # Time in seconds to check for new videos