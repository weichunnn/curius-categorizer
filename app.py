import streamlit as st
import pandas as pd
from brain import process, update_link

def main():
    st.title("Link Topic Categorizer")

    # Added help text to the User ID input
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

    if st.button("Fetch and Categorize Links"):
        global USER_ID
        USER_ID = int(user_id)

        progress_bar = st.progress(0) 
        st.session_state.results = process(empty_links=empty_links_bool, progress=progress_bar)

        if st.session_state.results:
            st.balloons()
            st.success("Links fetched and topics categorized successfully!")
    
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
