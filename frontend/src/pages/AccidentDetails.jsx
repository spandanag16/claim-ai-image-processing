import { useState } from "react";
import { useNavigate } from "react-router-dom";

const ACCIDENT_TYPES = ["Minor collision", "Major collision", "Scratch / parking damage", "Glass breakage", "Roll-over", "Other"];

function AccidentDetails() {
  const navigate = useNavigate();
  const [accident, setAccident] = useState(() => {
    const saved = JSON.parse(localStorage.getItem("claimData")) || {};
    return saved.accident || {
      date: "", time: "", location: "", type: "", other_vehicle: "",
      vehicle_drivable: "", description: "",
    };
  });
  const [error, setError] = useState("");

  const update = (field) => (event) => setAccident((previous) => ({ ...previous, [field]: event.target.value }));

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!accident.date || !accident.time || !accident.location || !accident.type || !accident.other_vehicle || !accident.vehicle_drivable) {
      setError("Please provide all accident details, including vehicle involvement and drivability.");
      return;
    }
    const existing = JSON.parse(localStorage.getItem("claimData")) || {};
    localStorage.setItem("claimData", JSON.stringify({ ...existing, accident }));
    navigate("/new-claim/images");
  };

  return (
    <div className="app claim-page">
      <header className="claim-header"><button type="button" className="back-button" onClick={() => navigate("/new-claim")}>← Vehicle</button><div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div><div className="claim-id">STEP 02 / 03</div></header>
      <main className="claim-container">
        <div className="claim-heading">
          <div className="badge">ACCIDENT DETAILS</div>
          <h1>Tell us what happened</h1>
          <p>Accident context is recorded in the claim report alongside the detected damage.</p>
        </div>

        <form className="claim-form accident-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="date">Date of Accident</label>
            <input id="date" type="date" value={accident.date} onChange={update("date")} />
          </div>
          <div className="form-group">
            <label htmlFor="time">Time of Accident</label>
            <input id="time" type="time" value={accident.time} onChange={update("time")} />
          </div>
          <div className="form-group">
            <label htmlFor="location">Location</label>
            <input id="location" value={accident.location} onChange={update("location")} placeholder="e.g. Indiranagar, Bengaluru" />
          </div>
          <div className="form-group">
            <label htmlFor="type">Accident Type</label>
            <select id="type" value={accident.type} onChange={update("type")}>
              <option value="">Select type</option>
              {ACCIDENT_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="other_vehicle">Another Vehicle Involved?</label>
            <select id="other_vehicle" value={accident.other_vehicle} onChange={update("other_vehicle")}>
              <option value="">Select an option</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
              <option value="Unknown">Unknown</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="vehicle_drivable">Is the Vehicle Drivable?</label>
            <select id="vehicle_drivable" value={accident.vehicle_drivable} onChange={update("vehicle_drivable")}>
              <option value="">Select an option</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
              <option value="Partially">Partially</option>
            </select>
          </div>
          <div className="form-group full-width">
            <label htmlFor="description">Incident Description</label>
            <input id="description" value={accident.description} onChange={update("description")} placeholder="Short description of the incident" />
          </div>
          {error && <div className="form-error full-width">{error}</div>}
          <div className="form-footer full-width">
            <span>{accident.type || "Continue to image upload"}</span>
            <button type="submit" className="primary-btn">Continue <span>→</span></button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default AccidentDetails;
