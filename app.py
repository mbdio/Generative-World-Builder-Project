import streamlit as st
import random
# from transformers import set_seed # For reproducibility with some local models, not directly used with Gemini API.
import google.generativeai as genai # Google's Generative AI SDK for Gemini

# --- Page Config (Optional but good) ---
# Sets the browser tab title and layout mode for the Streamlit app.
# "wide" layout uses the full browser width.
st.set_page_config(page_title="World Weaver RPG", layout="wide")

# --- Auth & Setup ---
# This block handles the authentication and initialization of the Gemini AI model.
try:
    # Retrieve the API key from Streamlit's secure secrets management.
    # On Streamlit Community Cloud, you set this in your app's settings.
    API_KEY = st.secrets.get("GEMINI_API_KEY")
    if not API_KEY:
        # If the API key is not found, display an error and stop the app.
        st.error("GEMINI_API_KEY not found in Streamlit secrets. Please add it.")
        st.stop() # Halts further execution of the script.

    # Configure the google.generativeai library with your API key.
    genai.configure(api_key=API_KEY)

    # Define the specific Gemini model to use.
    # "gemini-1.5-flash-latest" is a good balance of speed and capability.
    # Other models like "gemini-1.0-pro" could also be used.
    MODEL_NAME = "gemini-1.5-flash-latest"
    model = genai.GenerativeModel(MODEL_NAME) # Create a model instance.

except Exception as e:
    # Catch any errors during setup (e.g., invalid API key, network issues).
    st.error(f"Error during AI model setup: {e}")
    st.stop() # Stop the app if setup fails.

# --- Initialize Session State ---
# Streamlit reruns the script on most interactions. st.session_state is used to
# persist variables across these reruns, maintaining the application's state.

if 'current_world_profile' not in st.session_state:
    st.session_state.current_world_profile = None
if 'current_world_elements' not in st.session_state:
    st.session_state.current_world_elements = {'factions': [], 'races': [], 'skills': [], 'roles': []}
if 'current_story_log' not in st.session_state:
    st.session_state.current_story_log = []
if 'player_memory_bank' not in st.session_state:
    st.session_state.player_memory_bank = []
if 'character' not in st.session_state:
    st.session_state.character = None
if 'game_stage' not in st.session_state:
    st.session_state.game_stage = "world_creation"
if 'storyline_hook' not in st.session_state:
    st.session_state.storyline_hook = ""
if 'genre' not in st.session_state:
    st.session_state.genre = ""
# Explicitly initialize the key for the world description input text_area
if 'world_desc_input_key' not in st.session_state:
    st.session_state.world_desc_input_key = ""


# --- AI Functions ---
def generate_world_profile_ai(description: str) -> tuple:
    profile_prompt = (
        "Create a detailed Markdown world profile including:\n"
        "## World Name\n## Genre\n## Factions (bullet list with 'Name: Description')\n"
        "## Races (bullet list with 'Name: Traits')\n## Skills (bullet list of relevant abilities)\n"
        "## Roles (list of possible roles in this world, with descriptions)\n"
        "Add other sections like Geography, Culture, etc.\n\n"
        "Rules:\n- Use strict Markdown formatting\n- No speculative language\n"
        "- Avoid phrases like 'Let's see' or 'Okay'\n- Direct factual descriptions only\n"
        "- Never comment on the creation process"
    )
    try:
        response = model.generate_content([profile_prompt, description])
        profile = response.text
        extract_prompt = (
            "From this world profile, extract ONLY:\n"
            "- Faction names (comma-separated)\n- Race names (comma-separated)\n"
            "- Skill names (comma-separated)\n- Role names (comma-separated)\n"
            "Use format:\n"
            "FACTIONS: [names]\nRACES: [names]\nSKILLS: [names]\nROLES: [names]"
        )
        extraction_response = model.generate_content([extract_prompt, profile])
        extraction_text = extraction_response.text
        elements = {'factions': [], 'races': [], 'skills': [], 'roles': []}
        for line in extraction_text.split('\n'):
            if line.startswith('FACTIONS:'):
                elements['factions'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
            elif line.startswith('RACES:'):
                elements['races'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
            elif line.startswith('SKILLS:'):
                elements['skills'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
            elif line.startswith('ROLES:'):
                elements['roles'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
        return profile, elements
    except Exception as e:
        st.error(f"Error generating world profile: {e}")
        return None, {'factions': [], 'races': [], 'skills': [], 'roles': []}

def generate_random_theme_ai():
    try:
        response = model.generate_content(["Produce a fresh, single-sentence RPG world theme."])
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating random theme: {e}")
        return "A mysterious forest where ancient secrets sleep."

def generate_storyline_hook_ai(world_profile):
    if not world_profile:
        return "The world awaits its story."
    prompt = (
        f"Based on this world profile, generate a concise, one-sentence storyline hook: {world_profile}\n"
        "Rules:\n- No introductory phrases\n- Begin directly with the hook\n"
        "- Maintain in-universe perspective\n- Avoid meta-commentary"
    )
    try:
        response = model.generate_content([prompt])
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating storyline hook: {e}")
        return "An unexpected event shatters the peace..."

def continue_story_ai(world_profile, genre, storyline_hook, previous_story_segment, character_info, player_action):
    world_context = world_profile
    if len(world_profile) > 1500: # Summarize if world profile is very long for context window
        world_name_line = next((line for line in world_profile.split('\n') if "## World Name" in line), "## World Name\nUnknown World")
        genre_line = next((line for line in world_profile.split('\n') if "## Genre" in line), "## Genre\nUnknown Genre")
        world_context = f"{world_name_line}\n{genre_line}\n## Key Factions\n{st.session_state.current_world_elements.get('factions', [])[:3]}\n## Brief Summary\n... Core conflict or theme ..."
    
    prompt = (
        f"World Context: {world_context}\nGenre: {genre}\n"
        f"Overall Storyline Goal: {storyline_hook}\nPrevious Scene: {previous_story_segment}\n"
        f"Character: {character_info['name']} ({character_info.get('role', 'N/A')}, {character_info.get('race', 'N/A')}) - {character_info['description']}\nPlayer's Action: {player_action}\n\n"
        "Rules:\n- Continue the narrative directly from the player's action or current situation.\n"
        "- The story segment should be engaging and concise, approximately 2-3 short paragraphs or around 300 characters. Focus on quality over quantity.\n" # MODIFIED for length
        "- No filler phrases. Be direct.\n- Maintain in-universe perspective.\n- Show, don't tell.\n"
        "- Describe events, character thoughts (briefly), and dialogue.\n"
        "- End the segment at a point that naturally invites the player to make another decision or take another action.\n"
        "- Never use phrases like 'Okay' or 'Let's see'."
    )
    try:
        response = model.generate_content([prompt])
        return response.text.strip()
    except Exception as e:
        st.error(f"Error continuing story: {e}")
        return "The path ahead is shrouded in uncertainty..."

# --- UI Sections ---
st.title("🌍 World Weaver RPG")

# --- World Creation Section ---
if st.session_state.game_stage == "world_creation":
    st.header("1. Describe Your World")
    st.text_area(
        "Enter a description for your world, or get a random world:",
        height=100,
        key="world_desc_input_key"
    )

    col1, col2 = st.columns([1,5])
    with col1:
        if st.button("💡 Random", key="random_theme_btn"):
            random_theme = generate_random_theme_ai()
            st.session_state.world_desc_input_key = random_theme
    with col2:
        if st.button("✨ Generate World Profile", type="primary", key="generate_world_btn"):
            if st.session_state.world_desc_input_key:
                with st.spinner("Crafting your world..."):
                    profile, elements = generate_world_profile_ai(st.session_state.world_desc_input_key)
                if profile:
                    st.session_state.current_world_profile = profile
                    st.session_state.current_world_elements = elements
                    st.session_state.game_stage = "storyline_setup"
                    st.rerun()
            else:
                st.warning("Please enter a world description or generate a random theme.")

    if st.session_state.current_world_profile and st.session_state.game_stage != "storyline_setup":
        st.subheader("Generated World Profile Preview:")
        st.markdown(st.session_state.current_world_profile[:500] + "...")
        if st.button("Proceed with this world", key="proceed_world_confirm"):
            st.session_state.game_stage = "storyline_setup"
            st.rerun()

# --- Storyline and Genre Section ---
if st.session_state.game_stage == "storyline_setup":
    st.header("2. Setup Storyline & Genre")
    st.markdown("### World Profile Snippet:")
    # Displaying a snippet for brevity in this section
    st.markdown(st.session_state.current_world_profile[:1000] + "..." if len(st.session_state.current_world_profile) > 1000 else st.session_state.current_world_profile)
    
    st.text_input("Enter Genre (e.g., Fantasy, Sci-Fi):", key="genre")

    if st.button("🎲 Randomize Storyline Hook", key="random_storyline_btn"):
        st.session_state.storyline_hook = generate_storyline_hook_ai(st.session_state.current_world_profile)

    st.text_area("Storyline Hook:", key="storyline_hook", height=75)

    if st.button("✔️ Confirm Storyline & Genre", type="primary", key="confirm_storyline_btn"):
        if st.session_state.storyline_hook and st.session_state.genre:
            st.session_state.game_stage = "character_creation"
            st.rerun()
        else:
            st.warning("Please provide both a genre and a storyline hook.")

# --- Character Creation Section ---
if st.session_state.game_stage == "character_creation":
    st.header("3. Create Your Character")
    elements = st.session_state.current_world_elements

    with st.form("character_form"):
        char_name = st.text_input("Name:")
        char_desc = st.text_area("Description:", height=75)
        char_race_options = elements.get('races', [])
        char_race = st.selectbox("Race:", options=char_race_options if char_race_options else ["(No races defined)"])
        char_faction_options = elements.get('factions', [])
        char_faction = st.selectbox("Faction:", options=char_faction_options if char_faction_options else ["(No factions defined)"])
        char_role_options = elements.get('roles', [])
        char_role = st.selectbox("Role:", options=char_role_options if char_role_options else ["(No roles defined)"])
        char_skills_options = elements.get('skills', [])
        char_skills = st.multiselect("Skills (select one or more):", options=char_skills_options if char_skills_options else ["(No skills defined)"])
        submitted_char_form = st.form_submit_button("Begin Campaign", type="primary")

    if submitted_char_form:
        if char_name and char_desc:
            st.session_state.character = {
                'name': char_name,
                'description': char_desc,
                'race': char_race if char_race_options else "N/A",
                'faction': char_faction if char_faction_options else "N/A",
                'role': char_role if char_role_options else "N/A",
                'skills': char_skills if char_skills_options else []
            }
            st.session_state.game_stage = "campaign_init"
            with st.spinner("The adventure begins..."):
                initial_story_prompt = (
                    f"Character: {st.session_state.character['name']} - {st.session_state.character['description']}.\n"
                    "Start the narrative with an engaging opening scene for this character in the specified world and genre, "
                    "based on the storyline hook. The scene should leave room for the player to decide their first action."
                )
                first_story_segment = continue_story_ai(
                    st.session_state.current_world_profile,
                    st.session_state.genre,
                    st.session_state.storyline_hook,
                    "The story is just beginning.",
                    st.session_state.character,
                    initial_story_prompt
                )
            st.session_state.current_story_log = [first_story_segment]
            st.session_state.player_memory_bank = []
            st.session_state.game_stage = "campaign"
            st.rerun()
        else:
            st.warning("Please provide at least a character name and description.")

# --- Campaign Section ---
if st.session_state.game_stage == "campaign":
    world_info_col, story_col = st.columns([1, 2]) # Ratio 1:2 for World Info | Story

    with world_info_col:
        st.subheader("🌍 World Context")
        if st.session_state.current_world_profile:
            # Full profile is available in an expander, not truncated.
            with st.expander("Full World Profile", expanded=False):
                st.markdown(st.session_state.current_world_profile)
            
            st.markdown(f"**Genre:** {st.session_state.genre}")
            st.markdown(f"**Storyline Hook:** {st.session_state.storyline_hook}")
            elements = st.session_state.current_world_elements
            if elements.get('factions'):
                st.markdown(f"**Key Factions:** {', '.join(elements['factions'][:3])}...")
            if elements.get('races'):
                st.markdown(f"**Key Races:** {', '.join(elements['races'][:3])}...")

        st.subheader("👤 Character")
        if st.session_state.character:
            char = st.session_state.character
            st.markdown(f"**Name:** {char['name']}")
            st.markdown(f"**Description:** {char['description']}")
            st.markdown(f"**Race:** {char.get('race', 'N/A')}")
            st.markdown(f"**Faction:** {char.get('faction', 'N/A')}")
            st.markdown(f"**Role:** {char.get('role', 'N/A')}")
            if char.get('skills'):
                st.markdown(f"**Skills:** {', '.join(char['skills'])}")
        st.markdown("---")
        if st.button("🛑 End Campaign", key="end_campaign_btn_sidebar"):
            st.session_state.game_stage = "campaign_end"
            st.rerun()

    with story_col:
        st.header("⚔️ Your Adventure")
        st.markdown("---")
        story_container = st.container(height=500) # Scrollable container for the story log
        with story_container:
            # Each story entry is displayed fully.
            for entry in st.session_state.current_story_log:
                st.markdown(entry)
                st.markdown("---")

        player_action = st.text_input("What do you do next?", key=f"player_action_{len(st.session_state.current_story_log)}")

        if st.button("▶️ Continue", type="primary", key=f"continue_btn_{len(st.session_state.current_story_log)}"):
            if player_action:
                st.session_state.player_memory_bank.append(player_action)
                previous_segment = st.session_state.current_story_log[-1] if st.session_state.current_story_log else "The adventure has just begun."
                with st.spinner("The story unfolds..."):
                    next_segment = continue_story_ai(
                        st.session_state.current_world_profile,
                        st.session_state.genre,
                        st.session_state.storyline_hook,
                        previous_segment,
                        st.session_state.character,
                        player_action
                    )
                st.session_state.current_story_log.append(next_segment)
                st.rerun()
            else:
                st.warning("Please describe your action.")

# --- Campaign End Section ---
if st.session_state.game_stage == "campaign_end":
    st.header("📜 Campaign Log")
    col_log, col_story = st.columns(2)
    with col_log:
        st.subheader("Player Actions:")
        if st.session_state.player_memory_bank:
            for i, action in enumerate(st.session_state.player_memory_bank, 1):
                st.markdown(f"{i}. {action}")
        else:
            st.markdown("*No actions were logged in this adventure.*")

    with col_story:
        st.subheader("Full Narrative:")
        # Full narrative is displayed here without truncation.
        for entry in st.session_state.current_story_log:
            st.markdown(entry)
            st.markdown("---")

    if st.button("↩️ Start New World", type="primary", key="restart_btn"):
        keys_to_reset = [
            'current_world_profile', 'current_world_elements', 'current_story_log',
            'player_memory_bank', 'character', 'storyline_hook', 'genre',
            'world_desc_input_key' 
        ]
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        # Re-initialize keys for input widgets to ensure they are blank
        st.session_state.world_desc_input_key = "" 
        st.session_state.genre = ""
        st.session_state.storyline_hook = ""
        st.session_state.game_stage = "world_creation"
        st.rerun()

# --- Debugging Section (Commented Out) ---
# st.sidebar.header("Debug Info")
# st.sidebar.json(st.session_state)
