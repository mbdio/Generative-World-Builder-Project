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

# Check if 'current_world_profile' exists in session_state; if not, initialize it.
# This will store the full Markdown text of the generated world.
if 'current_world_profile' not in st.session_state:
    st.session_state.current_world_profile = None

# Stores structured data extracted from the world profile (factions, races, etc.).
if 'current_world_elements' not in st.session_state:
    st.session_state.current_world_elements = {'factions': [], 'races': [], 'skills': [], 'roles': []}

# Stores the history of the RPG story as a list of text segments.
if 'current_story_log' not in st.session_state:
    st.session_state.current_story_log = []

# Stores a log of actions taken by the player.
if 'player_memory_bank' not in st.session_state:
    st.session_state.player_memory_bank = []

# Stores the player character's details (name, description, race, etc.) as a dictionary.
if 'character' not in st.session_state:
    st.session_state.character = None

# Manages the current stage of the application (e.g., world creation, character creation, campaign).
# This controls which UI elements are displayed.
if 'game_stage' not in st.session_state:
    st.session_state.game_stage = "world_creation"

# Stores the main storyline hook for the RPG.
if 'storyline_hook' not in st.session_state:
    st.session_state.storyline_hook = ""

# Stores the genre of the world/story.
if 'genre' not in st.session_state:
    st.session_state.genre = ""


# --- AI Functions ---

# Generates a detailed world profile using the AI and extracts key elements.
def generate_world_profile_ai(description: str) -> tuple:
    # Prompt to instruct the AI on how to create the world profile.
    # It specifies the desired Markdown structure and content sections.
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
        # First AI call: Generate the full world profile.
        # The 'contents' argument takes a list of prompts/messages.
        response = model.generate_content([profile_prompt, description])
        profile = response.text # The AI's generated text.

        # Second AI call: Extract specific elements from the generated profile.
        # This prompt guides the AI to parse its previous output.
        extract_prompt = (
            "From this world profile, extract ONLY:\n"
            "- Faction names (comma-separated)\n- Race names (comma-separated)\n"
            "- Skill names (comma-separated)\n- Role names (comma-separated)\n"
            "Use format:\n"
            "FACTIONS: [names]\nRACES: [names]\nSKILLS: [names]\nROLES: [names]"
        )
        extraction_response = model.generate_content([extract_prompt, profile])
        extraction_text = extraction_response.text

        # Initialize a dictionary to store the extracted lists.
        elements = {'factions': [], 'races': [], 'skills': [], 'roles': []}
        # Parse the AI's extraction response line by line.
        # This relies on the AI strictly following the specified output format.
        for line in extraction_text.split('\n'):
            if line.startswith('FACTIONS:'):
                # Split the line at the first ':', take the second part (the names),
                # split by comma, strip whitespace from each name, and filter out empty strings.
                elements['factions'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
            elif line.startswith('RACES:'):
                elements['races'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
            elif line.startswith('SKILLS:'):
                elements['skills'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
            elif line.startswith('ROLES:'):
                elements['roles'] = [x.strip() for x in line.split(':',1)[1].split(',') if x.strip()]
        return profile, elements # Return the full profile and the extracted elements.
    except Exception as e:
        # If any error occurs during AI calls or parsing, display it in the Streamlit app.
        st.error(f"Error generating world profile: {e}")
        # Return default empty values.
        return None, {'factions': [], 'races': [], 'skills': [], 'roles': []}

# Generates a random, single-sentence RPG world theme using the AI.
def generate_random_theme_ai():
    try:
        response = model.generate_content(["Produce a fresh, single-sentence RPG world theme."])
        return response.text.strip() # Return the theme, removing extra whitespace.
    except Exception as e:
        st.error(f"Error generating random theme: {e}")
        return "A mysterious forest where ancient secrets sleep." # Provide a fallback theme on error.

# Generates a storyline hook based on the given world profile.
def generate_storyline_hook_ai(world_profile):
    if not world_profile: # If no world profile is provided, return a default message.
        return "The world awaits its story."
    # Prompt for the AI, using the world_profile as context.
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
        return "An unexpected event shatters the peace..." # Fallback hook on error.

# Generates the next segment of the RPG story based on various contexts and player action.
def continue_story_ai(world_profile, genre, storyline_hook, previous_story_segment, character_info, player_action):
    # Prepare a concise world context, especially if the full profile is very long,
    # to avoid exceeding the AI model's context window limit.
    world_context = world_profile
    if len(world_profile) > 1500: # Arbitrary length threshold for summarization.
        # Attempt to extract key parts like World Name and Genre.
        world_name_line = next((line for line in world_profile.split('\n') if "## World Name" in line), "## World Name\nUnknown World")
        genre_line = next((line for line in world_profile.split('\n') if "## Genre" in line), "## Genre\nUnknown Genre")
        # Construct a shorter context string.
        world_context = f"{world_name_line}\n{genre_line}\n## Key Factions\n{st.session_state.current_world_elements.get('factions', [])[:3]}\n## Brief Summary\n... Core conflict or theme ..."

    # Detailed prompt for the AI to continue the story.
    # Includes all relevant context: world, genre, storyline, previous scene, character, and player's action.
    # Specific rules guide the AI's narrative style and content.
    prompt = (
        f"World Context: {world_context}\nGenre: {genre}\n"
        f"Overall Storyline Goal: {storyline_hook}\nPrevious Scene: {previous_story_segment}\n"
        f"Character: {character_info['name']} ({character_info.get('role', 'N/A')}, {character_info.get('race', 'N/A')}) - {character_info['description']}\nPlayer's Action: {player_action}\n\n"
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
        return "The path ahead is shrouded in uncertainty..." # Fallback story segment on error.

# --- UI Sections ---
# The main title of the Streamlit application.
st.title("🌍 World Weaver RPG")

# --- World Creation Section ---
# This section is displayed only if the game_stage is 'world_creation'.
if st.session_state.game_stage == "world_creation":
    st.header("1. Describe Your World") # Section header.
    # Text area for user to input their world description.
    # The 'key' parameter links this widget's value to st.session_state.world_desc_input_key.
    # This allows us to access and update its content programmatically via session state.
    world_desc_input = st.text_area("Enter a description for your world, or get a random world:", height=100, key="world_desc_input_key")

    # Use columns for layout: one for random theme, one for generate button.
    col1, col2 = st.columns([1,5]) # col2 is 5 times wider than col1.
    with col1: # Content for the first column (Random button).
        if st.button("💡 Random", key="random_theme_btn"): # Changed label from "Random Theme"
            # When "Random" button is clicked:
            random_theme = generate_random_theme_ai() # Call AI to get a theme.
            # Update the text_area's content by setting its session state variable.
            # Streamlit will automatically reflect this change in the widget on the next rerun.
            st.session_state.world_desc_input_key = random_theme
    with col2: # Content for the second column (Generate World Profile button).
        # The 'type="primary"' argument makes the button more prominent.
        if st.button("✨ Generate World Profile", type="primary", key="generate_world_btn"):
            # When "Generate World Profile" button is clicked:
            # Check if there's input in the description box (accessed via its session state key).
            if st.session_state.world_desc_input_key:
                # Display a spinner while the AI processes the request.
                with st.spinner("Crafting your world..."):
                    profile, elements = generate_world_profile_ai(st.session_state.world_desc_input_key)
                if profile: # If profile generation was successful.
                    # Store the results in session state.
                    st.session_state.current_world_profile = profile
                    st.session_state.current_world_elements = elements
                    # Advance the game stage.
                    st.session_state.game_stage = "storyline_setup"
                    st.rerun() # Force Streamlit to rerun the script from the top.
                               # This updates the UI to reflect the new game_stage.
            else:
                # If no description is provided, show a warning.
                st.warning("Please enter a world description or generate a random theme.")

    # This block handles displaying a preview if a world was generated previously
    # but the app might have reran before fully transitioning.
    # It allows the user to confirm and proceed if they navigate away and back.
    if st.session_state.current_world_profile and st.session_state.game_stage != "storyline_setup":
        st.subheader("Generated World Profile Preview:")
        st.markdown(st.session_state.current_world_profile[:500] + "...") # Show a preview.
        if st.button("Proceed with this world", key="proceed_world_confirm"):
            st.session_state.game_stage = "storyline_setup" # Set stage to proceed.
            st.rerun()


# --- Storyline and Genre Section ---
# This section is displayed if game_stage is 'storyline_setup'.
if st.session_state.game_stage == "storyline_setup":
    st.header("2. Setup Storyline & Genre")
    st.markdown("### World Profile Snippet:")
    # Display a snippet of the world profile for context.
    # Shows first 1000 characters or full profile if shorter.
    st.markdown(st.session_state.current_world_profile[:1000] + "..." if len(st.session_state.current_world_profile) > 1000 else st.session_state.current_world_profile)
    
    # Text input for the game genre.
    # 'value' and 'key' ensure its state is preserved and can be updated.
    # The value entered by the user is automatically stored in st.session_state.genre due to the two-way binding nature when 'value' is st.session_state.variable.
    st.session_state.genre = st.text_input("Enter Genre (e.g., Fantasy, Sci-Fi):", value=st.session_state.genre, key="genre_input")

    if st.button("🎲 Randomize Storyline Hook", key="random_storyline_btn"):
        # Generate and update the storyline hook in session state when the button is clicked.
        st.session_state.storyline_hook = generate_storyline_hook_ai(st.session_state.current_world_profile)

    # Text area for the storyline hook.
    # It's pre-filled with any existing value in st.session_state.storyline_hook.
    st.session_state.storyline_hook = st.text_area("Storyline Hook:", value=st.session_state.storyline_hook, height=75, key="storyline_hook_input")

    if st.button("✔️ Confirm Storyline & Genre", type="primary", key="confirm_storyline_btn"):
        # Check if both genre and hook are provided.
        if st.session_state.storyline_hook and st.session_state.genre:
            st.session_state.game_stage = "character_creation" # Advance stage.
            st.rerun() # Rerun to show the character creation UI.
        else:
            st.warning("Please provide both a genre and a storyline hook.")

# --- Character Creation Section ---
# Displayed if game_stage is 'character_creation'.
if st.session_state.game_stage == "character_creation":
    st.header("3. Create Your Character")
    elements = st.session_state.current_world_elements # Get extracted world elements for dropdowns.

    # st.form groups widgets; their values are processed only when the form's submit button is clicked.
    # This prevents the app from rerunning on every change to an input field within the form.
    with st.form("character_form"):
        char_name = st.text_input("Name:") # Input for character name.
        char_desc = st.text_area("Description:", height=75) # Input for character description.
        
        # Get race options, providing a default list with a placeholder if none are available.
        char_race_options = elements.get('races', [])
        char_race = st.selectbox("Race:", options=char_race_options if char_race_options else ["(No races defined)"])
        
        char_faction_options = elements.get('factions', [])
        char_faction = st.selectbox("Faction:", options=char_faction_options if char_faction_options else ["(No factions defined)"])
        
        char_role_options = elements.get('roles', [])
        char_role = st.selectbox("Role:", options=char_role_options if char_role_options else ["(No roles defined)"])
        
        char_skills_options = elements.get('skills', [])
        # st.multiselect allows choosing multiple skills from the list.
        char_skills = st.multiselect("Skills (select one or more):", options=char_skills_options if char_skills_options else ["(No skills defined)"])

        # The submit button for the form. When clicked, 'submitted_char_form' becomes True.
        submitted_char_form = st.form_submit_button("Begin Campaign", type="primary")

    # This block executes only if the form's submit button ("Begin Campaign") was pressed.
    if submitted_char_form:
        if char_name and char_desc: # Basic validation: ensure name and description are filled.
            # Store character details in session state.
            # If options were empty (e.g., no races defined), store "N/A".
            st.session_state.character = {
                'name': char_name,
                'description': char_desc,
                'race': char_race if char_race_options else "N/A",
                'faction': char_faction if char_faction_options else "N/A",
                'role': char_role if char_role_options else "N/A",
                'skills': char_skills if char_skills_options else []
            }
            st.session_state.game_stage = "campaign_init" # Set an intermediate stage for initial story generation.
            with st.spinner("The adventure begins..."): # Show a loading spinner.
                # Prompt for the AI to generate the opening scene of the campaign.
                initial_story_prompt = (
                    f"Character: {st.session_state.character['name']} - {st.session_state.character['description']}.\n"
                    "Start the narrative with an engaging opening scene for this character in the specified world and genre, "
                    "based on the storyline hook. The scene should leave room for the player to decide their first action."
                )
                # Call AI to get the first story segment.
                first_story_segment = continue_story_ai(
                    st.session_state.current_world_profile,
                    st.session_state.genre,
                    st.session_state.storyline_hook,
                    "The story is just beginning.", # Context for the previous segment.
                    st.session_state.character,
                    initial_story_prompt # The "action" that kicks off the story.
                )
            st.session_state.current_story_log = [first_story_segment] # Initialize story log with the first segment.
            st.session_state.player_memory_bank = [] # Reset player action log for the new campaign.
            st.session_state.game_stage = "campaign" # Set stage for actual campaign play.
            st.rerun() # Rerun to display the campaign UI.
        else:
            st.warning("Please provide at least a character name and description.")


# --- Campaign Section ---
# Displayed if game_stage is 'campaign'.
if st.session_state.game_stage == "campaign":
    # Create two columns: one for persistent world/character info, one for the story.
    # The ratio [1, 2] means the story column (story_col) will be twice as wide as world_info_col.
    world_info_col, story_col = st.columns([1, 2])

    with world_info_col: # Content for the left (world info) column.
        st.subheader("🌍 World Context") # Header for world information.
        if st.session_state.current_world_profile: # Check if world profile exists.
            # Use st.expander to make the full world profile collapsible, saving space.
            with st.expander("Full World Profile", expanded=False): # Initially collapsed.
                st.markdown(st.session_state.current_world_profile) # Display full profile inside.
            
            # Display key world elements directly for quick reference.
            st.markdown(f"**Genre:** {st.session_state.genre}")
            st.markdown(f"**Storyline Hook:** {st.session_state.storyline_hook}")
            
            elements = st.session_state.current_world_elements
            if elements.get('factions'): # Show a few key factions if they exist.
                st.markdown(f"**Key Factions:** {', '.join(elements['factions'][:3])}...")
            if elements.get('races'): # Show a few key races if they exist.
                st.markdown(f"**Key Races:** {', '.join(elements['races'][:3])}...")

        st.subheader("👤 Character") # Character information section.
        if st.session_state.character: # If character data exists in session state.
            char = st.session_state.character # Get character details.
            # Display character attributes using Markdown for bolding labels.
            st.markdown(f"**Name:** {char['name']}")
            st.markdown(f"**Description:** {char['description']}")
            st.markdown(f"**Race:** {char.get('race', 'N/A')}") # Use .get() for safe access if key might be missing.
            st.markdown(f"**Faction:** {char.get('faction', 'N/A')}")
            st.markdown(f"**Role:** {char.get('role', 'N/A')}")
            if char.get('skills'): # If skills list is not empty.
                st.markdown(f"**Skills:** {', '.join(char['skills'])}")
        st.markdown("---") # Visual separator.
        # Button to end the campaign, placed in this persistent info panel.
        if st.button("🛑 End Campaign", key="end_campaign_btn_sidebar"):
            st.session_state.game_stage = "campaign_end" # Change game stage.
            st.rerun() # Rerun to show the end screen.


    with story_col: # Content for the right (story) column.
        st.header("⚔️ Your Adventure") # Header for the story part.
        st.markdown("---") # Visual separator.

        # Create a container with a fixed height for the story log.
        # If content (story segments) exceeds this height, it becomes scrollable.
        story_container = st.container(height=500)
        with story_container: # Story segments are displayed inside this container.
            # Display each segment of the story log.
            for entry in st.session_state.current_story_log:
                st.markdown(entry) # Display story segment as Markdown.
                st.markdown("---") # Separator between story segments.

        # Text input for the player's next action.
        # The key is made dynamic by including the length of the story log.
        # This helps Streamlit treat it as a "new" widget after an action is submitted,
        # which can help in clearing the input field implicitly on the next rerun.
        player_action = st.text_input("What do you do next?", key=f"player_action_{len(st.session_state.current_story_log)}")

        # Button for the player to submit their action and continue the story.
        # The key is also dynamic for similar reasons as the text_input.
        if st.button("▶️ Continue", type="primary", key=f"continue_btn_{len(st.session_state.current_story_log)}"):
            if player_action: # If the player entered an action.
                st.session_state.player_memory_bank.append(player_action) # Log the player's action.
                # Get the most recent story segment for AI context.
                previous_segment = st.session_state.current_story_log[-1] if st.session_state.current_story_log else "The adventure has just begun."
                with st.spinner("The story unfolds..."): # Show a loading spinner.
                    # Call AI to generate the next story segment based on current state and player action.
                    next_segment = continue_story_ai(
                        st.session_state.current_world_profile,
                        st.session_state.genre,
                        st.session_state.storyline_hook,
                        previous_segment,
                        st.session_state.character,
                        player_action
                    )
                st.session_state.current_story_log.append(next_segment) # Add new segment to story log.
                st.rerun() # Rerun to display the update and refresh input fields.
            else:
                st.warning("Please describe your action.") # Warn if no action is entered.

# --- Campaign End Section ---
# Displayed if game_stage is 'campaign_end'.
if st.session_state.game_stage == "campaign_end":
    st.header("📜 Campaign Log") # Main header for the end screen.
    
    # Use columns to display player actions and full narrative side-by-side.
    col_log, col_story = st.columns(2)
    with col_log: # Left column for player action log.
        st.subheader("Player Actions:")
        if st.session_state.player_memory_bank: # If actions were taken during the campaign.
            # Display numbered list of player actions.
            for i, action in enumerate(st.session_state.player_memory_bank, 1):
                st.markdown(f"{i}. {action}")
        else:
            st.markdown("*No actions were logged in this adventure.*")

    with col_story: # Right column for the full story narrative.
        st.subheader("Full Narrative:")
        # Display the complete story from the log.
        for entry in st.session_state.current_story_log:
            st.markdown(entry)
            st.markdown("---") # Separator.

    # Button to reset the game and start a new world.
    if st.button("↩️ Start New World", type="primary", key="restart_btn"):
        # Define a list of session state keys that should be cleared for a full game reset.
        keys_to_reset = [
            'current_world_profile', 'current_world_elements', 'current_story_log',
            'player_memory_bank', 'character', 'storyline_hook', 'genre', 
            'world_desc_input_key' # Also reset the world description input field's state.
        ]
        # Iterate and delete each key from session state if it exists.
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.game_stage = "world_creation" # Set game stage back to the beginning.
        st.rerun() # Rerun to refresh the UI to the initial world creation state.

# --- Debugging Section (Commented Out) ---
# These lines are very useful during development to inspect the current values
# of all variables stored in st.session_state.
# To use, uncomment them and check the Streamlit sidebar in your app.
# st.sidebar.header("Debug Info") # Adds a header to the Streamlit sidebar.
# st.sidebar.json(st.session_state) # Displays session_state as a nicely formatted JSON object.
