import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.llms import HuggingFaceHub
from htmlTemplates import css, bot_template, user_template


def get_datasheets_text(datasheets):
    """
        Extracts and concatenates text from multiple PDF datasheets.

        This function takes a list of PDF datasheet file paths, reads each PDF,
        and extracts text from all pages. The extracted text from each PDF is
        concatenated into a single string.

        Args:
            datasheets (list of str): A list of file paths to the PDF datasheets.

        Returns:
            str: A single string containing the concatenated text extracted from all pages of the provided PDF datasheets.
    """
    text = ""
    for datasheet in datasheets:
        pdf_reader = PdfReader(datasheet)
        for page in pdf_reader.pages:
            text += page.extract_text()

    return text


def get_text_chunks(raw_text):
    """
        Splits a large text into smaller chunks with specified size and overlap.

        This function uses a `CharacterTextSplitter` to split the input `raw_text`
        into chunks of a specified size. The chunks have a defined overlap to ensure
        that no information is lost between chunks.

        Args:
            raw_text (str): The raw text to be split into chunks.

        Returns:
            list of str: A list of text chunks generated from the input text. Each chunk
            has a maximum size of `chunk_size` characters and overlaps with the previous
            chunk by `chunk_overlap` characters.
    """
    text_splitter = CharacterTextSplitter(separator='\n',
                                          chunk_size=1000,
                                          chunk_overlap=200,
                                          length_function=len)
    text_chunks = text_splitter.split_text(raw_text)

    return text_chunks


def get_vectorstore(text_chunks):
    """
       Converts a list of text chunks into a vector store using embeddings.

       This function takes a list of text chunks and converts them into a vector
       store using embeddings generated by a selected embedding model. The vector
       store allows for efficient similarity search and retrieval of text chunks.

       Args:
           text_chunks (list of str): A list of text chunks to be converted into vectors.

       Returns:
           FAISS: A FAISS vector store containing the embedded text chunks,
           enabling fast similarity search operations.

       Note:
           The function currently uses the OpenAI Embeddings model for generating embeddings.
           An alternative embedding model, `HuggingFace Instructor-XL`, is also provided in
           the code but commented out. You can uncomment it and comment out the OpenAI
           Embeddings model line if you prefer to use it instead.
    """
    # OpenAI Embeddings Model
    embeddings = OpenAIEmbeddings()
    # HuggingFace Instructor-XL Embedding Model (Local)
    # embeddings = HuggingFaceInstructEmbeddings(model_name='hkunlp/instructor-xl')
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore


def get_conversation_chain(vectorstore):
    """
        Creates a conversational retrieval chain for interactive AI-driven conversations.

        This function sets up a conversational retrieval chain using a language model (LLM)
        and a vector store. The chain supports interactive conversations with memory, allowing
        it to recall previous exchanges. It integrates a retriever from the vector store to
        fetch relevant information during the conversation.

        Args:
            vectorstore (FAISS): A FAISS vector store that contains embedded text chunks
            and supports similarity-based retrieval.

        Returns:
            ConversationalRetrievalChain: A conversational retrieval chain that can be used
            for interactive conversations with memory, leveraging the provided vector store
            for retrieval.

        Note:
            The function uses the OpenAI LLM model by default. An alternative, the
            HuggingFace LLM model (`google/flan-t5-xxl`), is provided in the code but
            commented out. To use the HuggingFace model instead, uncomment the corresponding
            line and comment out the OpenAI LLM line.
    """
    # OpenAI LLM Model
    llm = ChatOpenAI()
    # HuggingFace LLM Model
    # llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature": 0.5, "max_length": 512})
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )

    return conversation_chain


def handle_userinput(user_question):
    """
        Handles the user's input and updates the conversation display.

        This function processes the user's question by passing it to the conversation
        chain stored in `st.session_state.conversation`. It retrieves the updated chat
        history and displays the conversation in the Streamlit app, alternating between
        user messages and bot responses.

        Args:
            user_question (str): The question or input provided by the user.

        Side Effects:
            Updates `st.session_state.chat_history` with the latest conversation history.
            Renders the conversation in the Streamlit app using predefined templates
            for user and bot messages.
    """
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    """
        The main function to initialize and run the ElectroGPT Streamlit app.

        This function sets up the Streamlit app interface, allowing users to upload
        datasheet PDFs, process them, and interact with an AI-powered conversational
        agent (ElectroGPT) that can answer queries based on the datasheets.

        Functionality includes:
        - Loading environment variables with `load_dotenv()`.
        - Configuring the Streamlit page settings (title, icon, etc.).
        - Initializing the session state for conversation and chat history.
        - Displaying the app header and an input field for user questions.
        - Handling user input to generate responses from the AI.
        - Providing a sidebar for users to upload PDF datasheets and process them to
          generate embeddings and create a conversational retrieval chain.

        The app displays the conversation dynamically, updating with each user interaction.

        Side Effects:
            Modifies `st.session_state` by storing conversation objects and chat history.
            Updates the Streamlit UI with user input, bot responses, and other elements.
    """
    load_dotenv()
    st.set_page_config(page_title="ElectroGPT", page_icon=":zap:")
    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header(":zap: ElectroGPT: Querying Datasheets Made Easy!")
    user_question = st.text_input("Ask a question regarding datasheets:")
    if user_question:
        handle_userinput(user_question)

    # st.write(user_template.replace("{{MSG}}", "Hello ElectroGPT!"), unsafe_allow_html=True)
    # st.write(bot_template.replace("{{MSG}}", "Hi!"), unsafe_allow_html=True)

    with st.sidebar:
        st.subheader("Your datasheets")
        datasheets = st.file_uploader("Upload your PDFs here and click on 'Process'", accept_multiple_files=True)
        if st.button('Process'):
            with st.spinner('Processing...'):
                # Get raw text from PDF datasheets
                raw_text = get_datasheets_text(datasheets)
                # Convert raw text into chunks
                text_chunks = get_text_chunks(raw_text)
                # Create vectorDB and create embeddings for text chunks, store into vectorDB
                vectorstore = get_vectorstore(text_chunks)
                # Create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)


if __name__ == '__main__':
    main()

