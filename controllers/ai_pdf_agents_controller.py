from fastapi import APIRouter, HTTPException, Query
from services.ai_pdf_agents_service import (
    PDFDownloaderService,
    CloudUploaderService,
    DocumentAnalyzerService,
    LLMSummarizerService,
)


router = APIRouter(prefix="/ai", tags=["AI Document Intelligence"])

# Initialize services
downloader = PDFDownloaderService()
uploader = CloudUploaderService()
analyzer = DocumentAnalyzerService()
summarizer = LLMSummarizerService()


@router.get("/summarize")
async def summarize_document(
    url: str = Query(
        ..., description="URL of the PDF document to process and summarize"
    )
):
    """
    📄 Uploads, analyzes, and summarizes a PDF document from a given URL.
    """
    try:
        # Step 1: Download PDF
        file_path = downloader.download(url)

        # Step 2: Upload to Azure Blob & generate SAS URL
        cloud_url = uploader.upload(file_path)

        # Step 3: Analyze content using Azure Document Intelligence
        analyzed_text = analyzer.analyze(cloud_url)

        # Cleanup local file
        import os

        if os.path.exists(file_path):
            os.remove(file_path)

        # Step 4: Summarize content using Groq + Agno
        if analyzed_text:
            return {
                "summary": summarizer.summarize(analyzed_text),
                "source": url,
                "status": "success",
            }

        raise HTTPException(
            status_code=400, detail="No readable content found in document."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
