import streamlit as st
import zipfile
import re
from collections import defaultdict
import base64
import streamlit.components.v1 as components

def process_text_files(zip_file):
    all_keywords = defaultdict(set)
    activation_tags = set()
    z = zipfile.ZipFile(zip_file)
    for filename in z.namelist():
        if filename.endswith('.txt'):
            with z.open(filename) as f:
                content = f.read().decode('utf-8')
                lines = content.strip().split('\n')
                for line in lines:
                    items = [item.strip() for item in line.strip().split(',')]
                    if not items:
                        continue

                    # Define the categories excluding 'Fabric' and 'Details' for initial mapping
                    category_order = [
                        "Activation Tag",
                        "Type of Clothing",
                        "Color",
                        "Fit",
                        "Neckline",
                        "Sleeves",
                        "Length"  # Optional, only for dresses
                    ]

                    data = {}
                    # Find the index of the first item that contains 'fabric'
                    fabric_indices = [i for i, item in enumerate(items) if 'fabric' in item.lower()]
                    if fabric_indices:
                        fabric_index = fabric_indices[0]
                    else:
                        fabric_index = None

                    # Map items before 'Fabric' to categories
                    num_categories = len(category_order)
                    for i in range(len(items)):
                        item = items[i]
                        if i == 0:
                            # Activation Tag
                            data['Activation Tag'] = item
                        elif fabric_index is not None and i == fabric_index:
                            # Fabric
                            data['Fabric'] = item
                        elif fabric_index is not None and i > fabric_index:
                            # After fabric
                            if 'fabric' in item.lower():
                                # Additional fabric
                                data['Fabric'] += ', ' + item
                            else:
                                # Details
                                data.setdefault('Details', []).append(item)
                        else:
                            # Before fabric
                            category_index = i
                            if category_index < num_categories:
                                category = category_order[category_index]
                                data[category] = item
                            else:
                                # Extra items before 'Fabric', handle as needed
                                pass

                    if fabric_index is None:
                        # No fabric found, process items up to the number of categories
                        for i in range(1, len(items)):
                            item = items[i]
                            category_index = i
                            if category_index < num_categories:
                                category = category_order[category_index]
                                data[category] = item
                            else:
                                # Assign remaining items to Details
                                data.setdefault('Details', []).append(item)

                    if data.get('Details'):
                        data['Details'] = ', '.join(data['Details'])

                    # Collect activation tag
                    activation_tags.add(data.get("Activation Tag"))
                    # Collect keywords for each category
                    for category in category_order[1:]:  # Skip activation tag
                        value = data.get(category)
                        if value:
                            all_keywords[category].add(value)
                    # Add Fabric
                    if data.get('Fabric'):
                        all_keywords['Fabric'].add(data['Fabric'])
                    # Add Details
                    if data.get('Details'):
                        all_keywords['Details'].add(data['Details'])

    return activation_tags, all_keywords

def main():
    st.set_page_config(layout="wide")
    st.markdown("""
    <style>
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    .stSelectbox, .stTextInput > div > div > input, .stMultiSelect {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    .stButton>button {
        color: #FFFFFF;
        background-color: #FF4B4B;
        border-radius: 5px;
    }
    .stTextArea > div > div > textarea {
        background-color: #FFFFFF;
        color: #000000;
    }
    .category-label {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 0.5em;
    }
    .category-container {
        margin-bottom: 1em;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("Prompt Generator")

    uploaded_file = st.file_uploader("텍스트 파일이 포함된 ZIP 파일을 업로드하세요", type="zip")

    all_keywords = defaultdict(set)
    activation_tags = set()

    if uploaded_file is not None:
        activation_tags, all_keywords = process_text_files(uploaded_file)

    # Handle activation tag
    activation_tag = None
    if activation_tags:
        if len(activation_tags) == 1:
            activation_tag = list(activation_tags)[0]
            st.write(f"Detected Activation Tag: {activation_tag}")
        else:
            activation_tag = st.selectbox("Select Activation Tag", options=sorted(activation_tags))
    else:
        activation_tag = st.text_input("Activation Tag", help="Enter the activation tag (e.g., go_dress)")

    col1, col2 = st.columns(2)

    prompt_parts = [activation_tag] if activation_tag else []

    # Categories in order
    category_order = [
        "Type of Clothing",
        "Color",
        "Fit",
        "Neckline",
        "Sleeves",
        "Length",  # Optional, only for dresses
        "Fabric",
        "Details"
    ]

    # Initialize selected values
    selected_values = {}

    # First column categories
    categories_col1 = ["Type of Clothing", "Color", "Fit", "Neckline"]
    # Second column categories
    categories_col2 = ["Sleeves", "Length", "Fabric", "Details"]

    # Collect selected type of clothing first to determine if Length is applicable
    with col1:
        for category in categories_col1:
            st.markdown(f'<div class="category-container"><p class="category-label">{category}</p></div>', unsafe_allow_html=True)
            options = [""] + sorted(all_keywords.get(category, []))
            selected = st.selectbox(label=f"{category} select", label_visibility="collapsed", options=options, key=f"{category}_select")
            selected_values[category] = selected
            if selected:
                prompt_parts.append(selected)

    with col2:
        for category in categories_col2:
            # Handle optional categories
            if category == "Length":
                # Include Length only if Type of Clothing is 'dress' or includes 'dress'
                type_of_clothing = selected_values.get("Type of Clothing", "").lower()
                if 'dress' in type_of_clothing:
                    display_length = True
                else:
                    display_length = False
            else:
                display_length = True  # For other categories

            if display_length:
                st.markdown(f'<div class="category-container"><p class="category-label">{category}</p></div>', unsafe_allow_html=True)
                options = sorted(all_keywords.get(category, []))
                if category == "Details":
                    selected = st.multiselect(label=f"{category} select", label_visibility="collapsed", options=options, key=f"{category}_select")
                else:
                    options = [""] + options
                    selected = st.selectbox(label=f"{category} select", label_visibility="collapsed", options=options, key=f"{category}_select")
                selected_values[category] = selected
                if selected:
                    # For Fabric category, only add if it ends with " fabric"
                    if category == "Fabric" and not selected.lower().endswith(" fabric"):
                        st.warning(f"Selected fabric '{selected}' does not end with ' fabric'. It will not be included in the prompt.")
                    elif category == "Details":
                        prompt_parts.extend(selected)
                    else:
                        prompt_parts.append(selected)
            else:
                # Skip this category
                selected_values[category] = None

    if st.button("Generate Prompt"):
        if prompt_parts:
            prompt = ", ".join(filter(None, prompt_parts))
            st.text_area("Generated Prompt", prompt, height=100)
            
            # Base64 encode the prompt to safely handle special characters
            prompt_b64 = base64.b64encode(prompt.encode()).decode()
            
            # Use components.html() to inject JavaScript that copies the prompt
            components.html(
                f"""
                <button onclick="navigator.clipboard.writeText(atob('{prompt_b64}')).then(function(){{alert('Prompt copied to clipboard!');}});">Copy Prompt</button>
                """,
                height=50,
            )
        else:
            st.info("Select keywords to generate a prompt")

if __name__ == "__main__":
    main()
