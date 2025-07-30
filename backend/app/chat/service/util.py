from typing import Tuple
import base64
import docx
import PyPDF2
from io import BytesIO
from app.chat.service.service import ILLMAdapter


async def extract_file_content(file_content: bytes, file_name: str, llm_client: ILLMAdapter) -> Tuple[str, str]:
    """Extract content from various file types."""
    file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''

    try:
        if file_extension == 'pdf':
            return await extract_pdf_content(file_content)
        elif file_extension in ['txt', 'py', 'js', 'csv', 'json', 'xml', 'html', 'css', 'md', 'go', 'ts']:
            return await extract_text_content(file_content, file_extension)
        elif file_extension in ['doc', 'docx']:
            return await extract_word_content(file_content, file_extension)
        elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            file_content_base64 = base64.b64encode(file_content).decode('utf-8')
            return await extract_image_content(file_content_base64, file_extension, llm_client)
        else:
            print(f"Unsupported file extension: .{file_extension}")
            return "", "unknown"
    except Exception as e:
        print(f"Error extracting content from {file_name}: {str(e)}")
        return "", "error"


async def extract_pdf_content(file_content: bytes) -> Tuple[str, str]:
    """Extract content from PDF files."""
    pdf_file = BytesIO(file_content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = "\n".join(page.extract_text() for page in pdf_reader.pages)
    return text, "pdf"


async def extract_text_content(file_content: bytes, file_extension: str) -> Tuple[str, str]:
    """Extract content from text-based files."""
    text = file_content.decode('utf-8', errors='ignore')
    if file_extension == 'csv':
        text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text, file_extension


async def extract_word_content(file_content: bytes, file_extension: str) -> Tuple[str, str]:
    """Extract content from Word documents."""
    doc_file = BytesIO(file_content)
    doc = docx.Document(doc_file)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    return text, file_extension


async def extract_image_content(base64_img: str, file_extension: str, llm_client: ILLMAdapter) -> Tuple[str, str]:
    """Extract content from images using OpenAI."""
    try:
        description = await llm_client.get_image_description(
            base64_image=base64_img,
            prompt="Please provide a detailed description of this image, including any visible text, key elements,"
                   " and overall context."
        )
        return description, file_extension
    except Exception as e:
        print(f"Error getting image description: {str(e)}")
        return "Error: Unable to extract image description", "error"

