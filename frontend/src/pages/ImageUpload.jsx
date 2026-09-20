import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../../api";

const MAX_IMAGES = 8;
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png"];

function ImageUpload() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const imagesRef = useRef([]);
  const [images, setImages] = useState([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    imagesRef.current = images;
  }, [images]);

  useEffect(() => () => {
    imagesRef.current.forEach((image) => URL.revokeObjectURL(image.preview));
  }, []);

  const processFiles = (files) => {
    setError("");
    setSuccessMessage("");
    const selectedFiles = Array.from(files);

    if (!selectedFiles.length) return;

    if (images.length + selectedFiles.length > MAX_IMAGES) {
      setError(`You can upload a maximum of ${MAX_IMAGES} images.`);
      return;
    }

    const validImages = [];
    const rejectedFiles = [];

    selectedFiles.forEach((file) => {
      const extension = file.name.split(".").pop()?.toLowerCase();
      const isSupported = ACCEPTED_TYPES.includes(file.type) && ["jpg", "jpeg", "png"].includes(extension);

      if (!isSupported) {
        rejectedFiles.push(`${file.name}: use JPG, JPEG, or PNG.`);
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        rejectedFiles.push(`${file.name}: larger than 10 MB.`);
        return;
      }

      validImages.push({
        id: `${file.name}-${file.lastModified}-${Math.random()}`,
        file,
        name: file.name,
        size: file.size,
        preview: URL.createObjectURL(file),
      });
    });

    if (rejectedFiles.length) setError(rejectedFiles.join(" "));
    setImages((previous) => [...previous, ...validImages]);
  };

  const handleFileSelect = (event) => {
    processFiles(event.target.files);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    processFiles(event.dataTransfer.files);
  };

  const removeImage = (id) => {
    setImages((previous) => {
      const imageToRemove = previous.find((image) => image.id === id);
      if (imageToRemove) URL.revokeObjectURL(imageToRemove.preview);
      return previous.filter((image) => image.id !== id);
    });
    setSuccessMessage("");
  };

  const handleContinue = async () => {
    setError("");
    setSuccessMessage("");

    if (images.length < 2) {
      setError("Please upload at least 2 images of the vehicle.");
      return;
    }

    setIsUploading(true);

    try {
      const preparedImages = [];
      for (const image of images) {
        const formData = new FormData();
        formData.append("file", image.file);
        const response = await API.post("/api/images/upload", formData);
        preparedImages.push(response.data);
      }

      const existingClaim = JSON.parse(localStorage.getItem("claimData")) || {};
      const updatedClaim = {
        ...existingClaim,
        images: preparedImages,
        imagePipeline: {
          status: "prepared",
          readyForYolo: true,
          uploadedAt: new Date().toISOString(),
        },
      };
      localStorage.setItem("claimData", JSON.stringify(updatedClaim));
      setSuccessMessage(`${preparedImages.length} images uploaded and prepared successfully.`);
      navigate("/new-claim/review");
    } catch (uploadError) {
      const detail = uploadError.response?.data?.detail;
      setError(detail || "Upload failed. Check that the backend is running and try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="claim-page">
      <header className="claim-header">
        <button className="back-button" onClick={() => navigate("/new-claim/accident")}>
          ← Accident Details
        </button>
        <div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div>
        <div className="claim-id">NEW CLAIM</div>
      </header>

      <div className="progress-container">
        <div className="progress-step completed"><div className="progress-number">✓</div><span>Vehicle</span></div>
        <div className="progress-line active-line" />
        <div className="progress-step completed"><div className="progress-number">✓</div><span>Accident</span></div>
        <div className="progress-line active-line" />
        <div className="progress-step active"><div className="progress-number">03</div><span>Images</span></div>
      </div>

      <main className="claim-container">
        <div className="claim-heading">
          <div className="badge">STEP 03 / 03</div>
          <h1>Show us the damage</h1>
          <p>Upload clear photographs from different angles. The backend validates and prepares each image for the future AI damage-detection stage.</p>
        </div>

        <div className="upload-area" onDrop={handleDrop} onDragOver={(event) => event.preventDefault()} onClick={() => fileInputRef.current?.click()}>
          <input ref={fileInputRef} type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" multiple hidden onChange={handleFileSelect} />
          <div className="upload-icon">↑</div>
          <h2>Drop your vehicle images here</h2>
          <p>or click to browse from your device</p>
          <span>JPG, JPEG or PNG · Maximum 10 MB per image · Up to 8 images</span>
        </div>

        {error && <div className="form-error upload-error">{error}</div>}
        {successMessage && <div className="upload-success">{successMessage}</div>}

        <div className="upload-header">
          <div><h3>Selected Images</h3><span>{images.length} / {MAX_IMAGES} images</span></div>
          {images.length > 0 && <button type="button" className="add-more-button" onClick={() => fileInputRef.current?.click()}>+ Add More</button>}
        </div>

        {images.length > 0 ? (
          <div className="image-grid">
            {images.map((image, index) => (
              <div className="image-card" key={image.id}>
                <img src={image.preview} alt={`Vehicle image ${index + 1}`} />
                <div className="image-overlay"><span>Image {index + 1}</span><button type="button" onClick={(event) => { event.stopPropagation(); removeImage(image.id); }}>×</button></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-images"><span>No images selected yet</span></div>
        )}

        <div className="upload-tips">
          <h3>For better AI results</h3>
          <div className="tips-grid">
            <div><strong>01</strong><span>Capture the vehicle from multiple angles.</span></div>
            <div><strong>02</strong><span>Take close-up photos of damaged areas.</span></div>
            <div><strong>03</strong><span>Avoid blurry or extremely dark images.</span></div>
          </div>
        </div>

        <div className="form-footer">
          <span>{isUploading ? "Preparing images…" : images.length === 0 ? "Upload at least 2 images to continue" : `${images.length} image${images.length > 1 ? "s" : ""} ready to upload`}</span>
          <button type="button" className="primary-btn" onClick={handleContinue} disabled={isUploading}>
            {isUploading ? "Uploading…" : "Upload & Continue"}<span>→</span>
          </button>
        </div>
      </main>
    </div>
  );
}

export default ImageUpload;
