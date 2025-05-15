import streamlit as st
import random
# from transformers import set_seed # set_seed might not be directly applicable or needed in the same way for Gemini API calls
import google.generativeai as genai

# --- Page Config (Optional but good) ---
st.set_page_config(page_title="World Weaver RPG", layout="wide")

# --- Auth & Setup ---
try:
    # For Streamlit Community Cloud, set API_KEY in the app's secrets
    API_KEY = st.secrets.get("GEMINI_API_KEY")
    if not API_KEY:
        st.error("GEMINI_API_KEY not found in Streamlit secrets. Please add it.")
        st.stop()
    genai.configure(api_key=API_KEY)
    # Use a valid and current model name
    MODEL_NAME = "gemini-1.5-flash-latest" # Or "gemini-1.0-pro", etc.
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"Error during AI model setup: {e}")
    st.stop()

# --- Initialize Session State ---
if 'current_world_profile' not in st.session_state:
    st.session_state.current_world_profile = None
if 'current_world_elements' not in st.session_state:
    st.session_state.current_world_elements = {'factions': [], 'races': [], 'skills': [], 'roles': []}
if 'current_story_log' not in st.session_state: # Will store full story dialogue
    st.session_state.current_story_log = []
if 'player_memory_bank' not in st.session_state: # Logs of player actions
    st.session_state.player_memory_bank = []
if 'character' not in st.session_state:
    st.session_state.character = None
if 'game_stage' not in st.session_state:
    st.session_state.game_stage = "world_creation" # Stages: world_creation, character_creation, storyline_setup, campaign, campaign_end
if 'storyline_hook' not in st.session_state:
    st.session_state.storyline_hook = ""
if 'genre' not in st.session_state:
    st.session_state.genre = ""


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
    prompt = (
        f"World Context (summary): {world_profile[:500]}...\nGenre: {genre}\n" # Send a summary if profile is too long
        f"Overall Storyline Goal: {storyline_hook}\nPrevious Scene: {previous_story_segment}\n"
        f"Character: {character_info['name']} - {character_info['description']}\nPlayer's Action: {player_action}\n\n"
        "Rules:\n- Continue the narrative directly from the player's action or current situation.\n"
        "- Keep the story segment engaging and around 2-4 paragraphs long.\n"
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
    world_desc_input = st.text_area("Enter a description for your world, or get a random theme:", height=100, key="world_desc_input_key")

    col1, col2 = st.columns([1,5]) # Adjust column ratios as needed
    with col1:
        if st.button("💡 Random Theme", key="random_theme_btn"):
            random_theme = generate_random_theme_ai()
            st.session_state.world_desc_input_key = random_theme # Update the text_area's content via its key
            # Automatically trigger generation or let user click "Generate World"
            # For now, just populates the box.

    with col2: # Or put generate button below text area
        if st.button("✨ Generate World Profile", type="primary", key="generate_world_btn"):
            if world_desc_input:
                with st.spinner("Crafting your world..."):
                    profile, elements = generate_world_profile_ai(world_desc_input)
                if profile:
                    st.session_state.current_world_profile = profile
                    st.session_state.current_world_elements = elements
                    st.session_state.game_stage = "storyline_setup" # Move to next stage
                    st.rerun() # Rerun to reflect stage change
            else:
                st.warning("Please enter a world description or generate a random theme.")

    if st.session_state.current_world_profile and st.session_state.game_stage != "storyline_setup": # If generated previously but not moved on
        st.subheader("Generated World Profile Preview:")
        st.markdown(st.session_state.current_world_profile[:500] + "...") # Preview
        if st.button("Proceed with this world", key="proceed_world_confirm"):
            st.session_state.game_stage = "storyline_setup"
            st.rerun()


# --- Storyline and Genre Section ---
if st.session_state.game_stage == "storyline_setup":
    st.header("2. Setup Storyline & Genre")
    st.markdown("### World Profile:")
    st.markdown(st.session_state.current_world_profile)
    
    st.session_state.genre = st.text_input("Enter Genre (e.g., Fantasy, Sci-Fi):", value=st.session_state.genre, key="genre_input")

    if st.button("🎲 Randomize Storyline Hook", key="random_storyline_btn"):
        st.session_state.storyline_hook = generate_storyline_hook_ai(st.session_state.current_world_profile)

    st.session_state.storyline_hook = st.text_area("Storyline Hook:", value=st.session_state.storyline_hook, height=75, key="storyline_hook_input")

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
        
        # Provide default empty list if options are not yet populated or empty
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
            st.session_state.game_stage = "campaign_init" # New stage to trigger initial story
            # Generate initial story part
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
                    initial_story_prompt # Using this as the "action" to kick things off
                )
            st.session_state.current_story_log.append(first_story_segment)
            st.session_state.game_stage = "campaign"
            st.rerun()
        else:
            st.warning("Please provide at least a character name and description.")


# --- Campaign Section ---
if st.session_state.game_stage == "campaign":
    st.header("⚔️ Your Adventure")
    st.markdown(f"**Character:** {st.session_state.character['name']} ({st.session_state.character.get('role', 'N/A')})")
    st.markdown(f"**World:** *(Excerpt)* {st.session_state.current_world_profile[:200]}...")
    st.markdown(f"**Storyline:** {st.session_state.storyline_hook}")
    st.markdown("---")

    # Display story log
    for entry in st.session_state.current_story_log:
        st.markdown(entry)
        st.markdown("---") # Separator for story parts

    # Player action
    player_action = st.text_input("What do you do next?", key=f"player_action_{len(st.session_state.current_story_log)}")

    col_act, col_end = st.columns(2)
    with col_act:
        if st.button("▶️ Continue", type="primary", key=f"continue_btn_{len(st.session_state.current_story_log)}"):
            if player_action:
                st.session_state.player_memory_bank.append(player_action)
                previous_segment = st.session_state.current_story_log[-1] if st.session_state.current_story_log else "The story has just begun."
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
                # Clear the input by rerunning; the key change will also help
                st.rerun()
            else:
                st.warning("Please describe your action.")
    with col_end:
        if st.button("🛑 End Campaign", key="end_campaign_btn"):
            st.session_state.game_stage = "campaign_end"
            st.rerun()

# --- Campaign End Section ---
if st.session_state.game_stage == "campaign_end":
    st.header("📜 Campaign Log")
    st.markdown("Your adventure has concluded. Here's a log of your character's actions:")
    if st.session_state.player_memory_bank:
        for i, action in enumerate(st.session_state.player_memory_bank, 1):
            st.markdown(f"{i}. {action}")
    else:
        st.markdown("*No actions were taken in this short adventure.*")

    st.markdown("### Full Story:")
    for entry in st.session_state.current_story_log:
        st.markdown(entry)
        st.markdown("---")

    if st.button("↩️ Start New World", key="restart_btn"):
        # Reset relevant session state variables
        for key in list(st.session_state.keys()): # Iterate over a copy of keys
            if key not in ['secrets_set_warning_shown']: # Don't clear all, especially if secrets has internal flags
                 if key.startswith("current_") or key.startswith("player_") or key == "character" or key == "game_stage" or key == "storyline_hook" or key == "genre":
                    del st.session_state[key]
        st.session_state.game_stage = "world_creation" # Explicitly set to start
        st.rerun()

# For debugging session state:
# st.sidebar.header("Debug Info")
# st.sidebar.write(st.session_state)
