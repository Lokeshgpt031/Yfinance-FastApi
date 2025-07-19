from abc import ABC, abstractmethod
import logging
import os
import requests
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
logger = logging.getLogger(__name__)
# Load environment
load_dotenv()

STORAGE_CONNECTION_STRING = os.getenv("StorageAccountConnectionString")
AIDocumentKey = os.getenv("AIDocumentKey")
ENDPOINT = "https://360documents.cognitiveservices.azure.com/"
CONTAINER_NAME = "ai-test"
MODEL = os.getenv("MODEL")
print("MODEL: ",MODEL)
# --------------------------------------------
# Interfaces
# --------------------------------------------

class IDownloadService(ABC):
    @abstractmethod
    def download(self, url: str) -> str:
        pass

class IUploadService(ABC):
    @abstractmethod
    def upload(self, file_path: str) -> str:
        pass

class IAnalyzeService(ABC):
    @abstractmethod
    def analyze(self, file_url: str) -> str:
        pass

class ISummarizerService(ABC):
    @abstractmethod
    def summarize(self, text: str) -> str:
        pass

# --------------------------------------------
# Implementations
# --------------------------------------------

class PDFDownloaderService(IDownloadService):
    def download(self, url: str) -> str:
        file_name = url.split("/")[-1]
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf"
        }
        response = requests.get(url, headers=headers, allow_redirects=True)

        if response.status_code == 200:
            with open(file_name, "wb") as f:
                f.write(response.content)
            logger.info("PDFDownloaderService is succeded")
            return file_name
        logger.info("PDFDownloaderService is failed")
        
        raise Exception(f"Failed to download. Status code: {response.status_code}")

class CloudUploaderService(IUploadService):
    def upload(self, file_path: str) -> str:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file_path)

            sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                account_key=blob_service_client.credential.account_key,
                container_name=CONTAINER_NAME,
                blob_name=file_path,
                permission=BlobSasPermissions(read=True, write=True),
                start=datetime.now(timezone.utc),
                expiry=datetime.now(timezone.utc) + timedelta(hours=1)
            )

            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            import os
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.info("CloudUploaderService is succeded")
            return f"{blob_client.url}?{sas_token}"
        except Exception as e:
            raise Exception(f"CloudUploaderService Failed: {e}")

class DocumentAnalyzerService(IAnalyzeService):
    def analyze(self, file_url: str) -> str:
        try:
            client = DocumentIntelligenceClient(endpoint=ENDPOINT, credential=AzureKeyCredential(AIDocumentKey))
            poller = client.begin_analyze_document("prebuilt-read", AnalyzeDocumentRequest(url_source=file_url))
            result = poller.result()
            logger.info("DocumentAnalyzerService is succeded")
            return result.content
        except Exception as e:
            raise Exception(f"Document Analysis Failed: {e}")

class LLMSummarizerService(ISummarizerService):
    def summarize(self, text: str) -> str:
        from agno.agent import Agent
        from agno.models.groq import Groq
        from agno.tools.duckduckgo import DuckDuckGoTools
        from agno.tools.yfinance import YFinanceTools

        web_agent = Agent(
            name="Market News Analyst",
            role="You are a skilled financial journalist. Your job is to analyze corporate documents, extract key decisions, and translate them into concise, readable summaries that help investors make sense of the news.",
            model=Groq(id=MODEL),
            tools=[DuckDuckGoTools()],
            show_tool_calls=True,
            instructions=(
                "Focus on extracting key highlights from the document such as: corporate actions, board decisions, dividends, mergers, acquisitions, and any changes in capital structure. "
                "Use bullet points or short paragraphs for clarity. Include relevant external information when needed. Provide source if data is referenced externally."
            ),
            markdown=True
        )

        finance_agent = Agent(
            name="Financial Data Assistant",
            role="You are a financial analyst. You retrieve factual data such as stock performance, valuations, and analyst insights for companies mentioned in the input text.",
            model=Groq(id=MODEL),
            tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
            instructions=(
                "For any company mentioned, retrieve stock price, recent trends, market cap, P/E ratio, and analyst recommendation. "
                "Present the data in clear tables. If no stock info is required, remain silent."
            ),
            markdown=True,
        )

        orchestrator = Agent(
            team=[web_agent, finance_agent],
            model=Groq(id=MODEL),
            instructions=[
                "Use the web agent to summarize textual content from the document.",
                "Use the finance agent only if companies or stock symbols are mentioned.",
                "Ensure the final summary is clear, organized, and includes external facts or price data if relevant.",
                "Always include headers, bullet points, and tables where applicable for readability."
            ],
            markdown=True
        )

        short_text = text[:1000] if len(text) > 1000 else text
        return orchestrator.run(short_text).content
