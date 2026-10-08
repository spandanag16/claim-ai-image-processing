import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../../api";

function ImageUpload() {

  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [images, setImages] = useState([]);
  const [error, setError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const MAX_IMAGES = 8;
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB


  // =========================
  // HANDLE FILES
  // =========================

  const processFiles = (files) => {

    setError("");

    const selectedFiles = Array.from(files);

    if (selectedFiles.length === 0) {
      return;
    }

    // Check maximum number of images

    if (images.length + selectedFiles.length > MAX_IMAGES) {

      setError(
        `You can upload a maximum of ${MAX_IMAGES} images.`
      );

      return;
    }


    const validImages = [];

    for (const file of selectedFiles) {

      // File type validation

      if (!file.type.startsWith("image/")) {

        setError(
          `${file.name} is not a valid image file.`
        );

        continue;
      }


      // File size validation

      if (file.size > MAX_FILE_SIZE) {

        setError(
          `${file.name} is larger than 10 MB.`
        );

        continue;
      }


      // Create preview

      const imageObject = {
        id:
          Date.now() +
          Math.random(),

        file: file,

        name: file.name,

        size: file.size,

        preview: URL.createObjectURL(file),
      };


      validImages.push(imageObject);
    }


    setImages((previous) => [
      ...previous,
      ...validImages,
    ]);

  };


  // =========================
  // FILE INPUT
  // =========================

  const handleFileSelect = (event) => {

    processFiles(event.target.files);

    // Allow selecting same file again
    event.target.value = "";

  };


  // =========================
  // DRAG & DROP
  // =========================

  const handleDrop = (event) => {

    event.preventDefault();

    processFiles(event.dataTransfer.files);

  };


  const handleDragOver = (event) => {

    event.preventDefault();

  };


  // =========================
  // REMOVE IMAGE
  // =========================

  const removeImage = (id) => {

    setImages((previous) => {

      const imageToRemove =
        previous.find(
          (image) => image.id === id
        );

      if (imageToRemove) {

        URL.revokeObjectURL(
          imageToRemove.preview
        );

      }

      return previous.filter(
        (image) => image.id !== id
      );

    });

  };


  // =========================
  // CONTINUE
  // =========================

  const handleContinue = async () => {
    setError("");

    if (images.length < 2) {
      setError("Please upload at least 2 images of the vehicle.");
      return;
    }

    const formData = new FormData();
    images.forEach((image) => formData.append("files", image.file));
    setIsAnalyzing(true);

    try {
      const { data: analysis } = await API.post("/api/analyze-claim", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const existingClaim = JSON.parse(localStorage.getItem("claimData")) || {};
      const imageInformation = images.map((image) => ({
        name: image.name,
        size: image.size,
      }));
      const updatedClaim = {
        ...existingClaim,
        images: imageInformation,
        analysis,
      };

      localStorage.setItem("claimData", JSON.stringify(updatedClaim));
      navigate("/claim/review");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Analysis failed. Make sure the backend is running and try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (

    <div className="claim-page">


      {/* =========================
          HEADER
      ========================= */}

      <header className="claim-header">

        <button
          className="back-button"
          onClick={() =>
            navigate("/new-claim/accident")
          }
        >
          ← Accident Details
        </button>


        <div className="logo">

          <span className="logo-icon">
            AI
          </span>

          <span>
            ClaimAI
          </span>

        </div>


        <div className="claim-id">
          NEW CLAIM
        </div>

      </header>



      {/* =========================
          PROGRESS
      ========================= */}

      <div className="progress-container">

        <div className="progress-step completed">

          <div className="progress-number">
            ✓
          </div>

          <span>
            Vehicle
          </span>

        </div>


        <div className="progress-line active-line"></div>


        <div className="progress-step completed">

          <div className="progress-number">
            ✓
          </div>

          <span>
            Accident
          </span>

        </div>


        <div className="progress-line active-line"></div>


        <div className="progress-step active">

          <div className="progress-number">
            03
          </div>

          <span>
            Images
          </span>

        </div>

      </div>



      {/* =========================
          MAIN
      ========================= */}

      <main className="claim-container">

        <div className="claim-heading">

          <div className="badge">
            STEP 03 / 03
          </div>

          <h1>
            Show us the damage
          </h1>

          <p>
            Upload clear photographs of the vehicle from
            different angles. Our AI will use these images
            to identify damaged parts and assess their severity.
          </p>

        </div>



        {/* =========================
            UPLOAD AREA
        ========================= */}

        <div
          className="upload-area"

          onDrop={handleDrop}

          onDragOver={handleDragOver}

          onClick={() =>
            fileInputRef.current?.click()
          }
        >

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            hidden
            onChange={handleFileSelect}
          />


          <div className="upload-icon">
            ↑
          </div>


          <h2>
            Drop your vehicle images here
          </h2>


          <p>
            or click to browse from your device
          </p>


          <span>
            JPG, PNG or WEBP · Maximum 10 MB per image
          </span>

        </div>



        {/* =========================
            ERROR
        ========================= */}

        {error && (

          <div className="form-error upload-error">
            {error}
          </div>

        )}



        {/* =========================
            IMAGE COUNT
        ========================= */}

        <div className="upload-header">

          <div>

            <h3>
              Uploaded Images
            </h3>

            <span>
              {images.length} / {MAX_IMAGES} images
            </span>

          </div>

          {images.length > 0 && (

            <button
              className="add-more-button"
              onClick={() =>
                fileInputRef.current?.click()
              }
            >
              + Add More
            </button>

          )}

        </div>



        {/* =========================
            IMAGE GRID
        ========================= */}

        {images.length > 0 ? (

          <div className="image-grid">

            {images.map((image, index) => (

              <div
                className="image-card"
                key={image.id}
              >

                <img
                  src={image.preview}
                  alt={`Vehicle damage ${index + 1}`}
                />


                <div className="image-overlay">

                  <span>
                    Image {index + 1}
                  </span>


                  <button
                    onClick={(event) => {

                      event.stopPropagation();

                      removeImage(image.id);

                    }}
                  >
                    ×
                  </button>

                </div>

              </div>

            ))}

          </div>

        ) : (

          <div className="empty-images">

            <span>
              No images uploaded yet
            </span>

          </div>

        )}



        {/* =========================
            IMAGE TIPS
        ========================= */}

        <div className="upload-tips">

          <h3>
            📸 For better AI results
          </h3>

          <div className="tips-grid">

            <div>
              <strong>01</strong>
              <span>
                Capture the vehicle from multiple angles.
              </span>
            </div>

            <div>
              <strong>02</strong>
              <span>
                Take close-up photos of damaged areas.
              </span>
            </div>

            <div>
              <strong>03</strong>
              <span>
                Avoid blurry or extremely dark images.
              </span>
            </div>

          </div>

        </div>



        {/* =========================
            FOOTER
        ========================= */}

        <div className="form-footer">

          <span>
            {images.length === 0
              ? "Upload at least 2 images to continue"
              : `${images.length} image${
                  images.length > 1 ? "s" : ""
                } ready for analysis`}
          </span>


          <button
            type="button"
            className="primary-btn"
            onClick={handleContinue}
            disabled={isAnalyzing}
          >

            {isAnalyzing ? "Analyzing images..." : "Continue to Review"}

            <span>
              →
            </span>

          </button>

        </div>

      </main>

    </div>

  );

}

export default ImageUpload;
