import streamlit as st
import pandas as pd
from brain import process, update_link

def main():
    st.set_page_config(page_title="Curius Link Categorizer")
    
    st.image('images/shelves.png', caption='Books on a Shelf')
    st.title("Curius Categorizer")
    st.write("This application helps you categorize your links effectively and efficiently. Simply enter your User ID, choose your preferences, and let the app do the rest!")

    st.header("User Configuration")
    user_id = st.text_input("Enter your User ID", "0000", help="Type your unique user ID here. If unsure, use the default value.")

    # Added help text to the radio button
    empty_links = st.radio(
        "Process empty links only?",
        ("Yes", "No"),
        index=0,
        help="Select 'Yes' to process only the links with no assigned topics. Select 'No' to process all links."
    )
    empty_links_bool = empty_links == "Yes"

    # Load or initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = None

    if st.button("Extract and Categorize Links"):
        global USER_ID
        USER_ID = int(user_id)

        st.write('#')
        st.info('This might take a while depending on OpenAI - go have some rest and come back!', icon="ℹ️")
        progress_bar = st.progress(0, text='Fetching your details from Curius') 
        st.session_state.results = process(empty_links=empty_links_bool, progress=progress_bar)

        if st.session_state.results:
            st.balloons()
            st.success("Links fetched and topics categorized successfully!")
            st.success(f"Total of {len(st.session_state.results)} processed!")
    
    if st.session_state.results:
        df_results = pd.DataFrame(st.session_state.results)
        df_results = df_results[['id', 'title', 'topics', 'url']]
        st.data_editor(
          df_results,
          column_config={
              "url": st.column_config.LinkColumn("url", display_text="🔗")
          },
          hide_index=True,
      )

        # Added help text to the Authorization Token input area
        auth_token = st.text_area("Enter your Authorization Token to update topics", help="Paste your authorization token here to enable topic updates ie Bearer XXX")

        if st.button("Update Topics"):
            global HEADERS
            HEADERS = {}
            HEADERS["Authorization"] = auth_token

            for index, result in df_results.iterrows():
                response = update_link(result['id'], result['topics'])
                if response:
                    st.success(f"Topics for link ID {result['id']} updated successfully.")
                else:
                    st.error(f"Failed to update topics for link ID {result['id']}.")

if __name__ == "__main__":
    main()
