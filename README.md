# Connecting the Dots Challenge - Round 1A Submission

This project is a solution for Round 1A of the "Connecting the Dots" Challenge. It's a Dockerized application that extracts a structured outline (Title, H1, H2, H3) from PDF documents.

## Approach

My approach focuses on creating a robust and efficient solution that works entirely offline and adheres to the specified performance constraints. The core of the solution is a heuristic-based analysis of the PDF's text properties.

1.  **PDF Parsing**: I chose the **PyMuPDF (fitz)** library for its exceptional performance and its ability to extract detailed information about text blocks, including font size, font name, boldness, and position. This is critical for accurate heading detection.

2.  **Dynamic Heading Classification**: Instead of relying on fixed font size rules (which can be unreliable), my solution first performs a statistical analysis of the entire document:
    *   It scans all text on all pages to build a frequency distribution of font sizes.
    *   The most frequently occurring font size is assumed to be the **body text**.
    *   Any text with a font size larger than the body text is considered a potential heading.

3.  **Hierarchical Structuring**:
    *   The identified heading font sizes are sorted in descending order.
    *   The largest size is mapped to **H1**, the second-largest to **H2**, and the third-largest to **H3**.
    *   The document's **Title** is inferred by identifying the text with the largest font size on the first page.

4.  **Final Extraction**: The script makes a second pass through the document, classifying each line of text based on the dynamic rules established in the analysis phase and outputting the final JSON structure. This two-pass approach makes the logic highly adaptable to different document styles without hardcoding.

## Libraries and Models

*   **Libraries**:
    *   `PyMuPDF` (fitz): A high-performance Python library for PDF processing.
*   **Models**:
    *   No external machine learning models are used. The solution is purely algorithmic to ensure it meets the **<200MB model size** constraint and works offline without dependencies.

## How to Build and Run

The solution is fully containerized using Docker and is designed to run with the exact commands specified in the challenge instructions.

### 1. Build the Docker Image

Navigate to the root directory of the project (where the `Dockerfile` is located) and run the following command. Replace `mysolutionname:somerandomidentifier` with your desired image name.

```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
```

### 2. Run the Solution

After building the image, use the following command to run the container. This command mounts your local `input` and `output` directories to the corresponding directories inside the container.

*   Ensure you have a folder named `input` in your current directory containing the PDF files you want to process.
*   The script will create an `output` folder in your current directory with the resulting `.json` files.

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none mysolutionname:somerandomidentifier
```

The container will automatically process all PDFs from the `/app/input` directory and exit upon completion. The extracted JSON files will be available in your local `output` directory.