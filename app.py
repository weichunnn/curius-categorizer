import pandas as pd
import streamlit as st

from brain import process, update_link


def main():
    st.set_page_config(page_title="Curius Link Categorizer")

    st.image("images/shelves.png", caption="Books on a Shelf")
    st.title("Curius Categorizer")
    st.write(
        "This application helps you categorize your links effectively and efficiently. Simply enter your User ID, choose your preferences, and let the app do the rest!"
    )

    st.header("User Configuration")
    user_id = st.text_input(
        "Enter your User ID",
        placeholder="0000",
        help="Type your unique user ID here. If unsure, use the default value.",
    )

    # Added help text to the radio button
    empty_links = st.radio(
        "Process empty links only?",
        ("Yes", "No"),
        index=0,
        help="Select 'Yes' to process only the links with no assigned topics. Select 'No' to process all links.",
    )
    empty_links_bool = empty_links == "Yes"

    # Load or initialize session state
    if "results" not in st.session_state:
        st.session_state.results = None

    st.write("#")

    st.info(
        "This button is safe! You will be prompted again if you decide to update your topics",
        icon="ℹ️",
    )
    if st.button("Extract and Categorize Links"):
        st.write("#")
        st.info(
            "This might take a while depending on OpenAI - go have some rest and come back!",
            icon="ℹ️",
        )
        progress_bar = st.progress(0, text="Fetching your details from Curius")
        st.session_state.results = process(
            user_id=user_id, empty_links=empty_links_bool, progress=progress_bar
        )

        if st.session_state.results:
            st.balloons()
            st.success("Links fetched and topics categorized successfully!")
            st.success(f"Total of {len(st.session_state.results)} links processed!")

    if st.session_state.results:
        df_results = pd.DataFrame(st.session_state.results)
        df_results = df_results[["id", "title", "topics", "url"]]
        st.data_editor(
            df_results,
            column_config={
                "url": st.column_config.LinkColumn("url", display_text="🔗")
            },
            hide_index=True,
            use_container_width=True,
        )

        # Added help text to the Authorization Token input area
        auth_token = st.text_input(
            "Enter your Authorization Token to update topics",
            help="Paste your authorization token here to enable topic updates ie Bearer XXX",
            type='password'

        )

        if st.button("Update Topics"):
            # Initialize the progress bar
            total = len(df_results)
            progress_bar = st.progress(0, text=f"Working hard - 0 / {total}")
            for index, result in enumerate(df_results.iterrows()):
                response = update_link(result[1]["id"], result[1]["topics"], auth_token)
                if not response:
                    st.error(f"Failed to update topics for link ID {result[1]['id']}.")

                progress_bar.progress(
                    (index + 1) / total, text=f"Working hard - {index + 1} / {total}"
                )

            st.success("All topics updated.")
            st.snow()


if __name__ == "__main__":
    main()
