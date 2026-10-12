import { useState } from "react";
import { useNavigate } from "react-router-dom";

const MANUFACTURERS = ["Maruti Suzuki", "Hyundai", "Tata", "Mahindra", "Honda", "Toyota", "Kia", "Volkswagen", "Other"];

function NewClaim() {
  const navigate = useNavigate();
  const [vehicle, setVehicle] = useState(() => {
    const saved = JSON.parse(localStorage.getItem("claimData")) || {};
    return saved.vehicle || { manufacturer: "", model: "", year: "", registration_number: "" };
  });
  const [error, setError] = useState("");

  const update = (field) => (event) => setVehicle((previous) => ({ ...previous, [field]: event.target.value }));

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!vehicle.manufacturer || !vehicle.model || !vehicle.year || !vehicle.registration_number) {
      setError("Please fill all vehicle details.");
      return;
    }
    const year = Number(vehicle.year);
    if (year < 1980 || year > new Date().getFullYear()) {
      setError("Manufacturing year must be between 1980 and today.");
      return;
    }
    const existing = JSON.parse(localStorage.getItem("claimData")) || {};
    localStorage.setItem("claimData", JSON.stringify({
      ...existing,
      claimId: existing.claimId || `CLM-${Date.now().toString(36).toUpperCase()}`,
      vehicle,
    }));
    navigate("/new-claim/accident");
  };

  return (
    <div className="app claim-page">
      <header className="claim-header"><div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div><div className="claim-id">NEW CLAIM</div></header>
      <main className="claim-container">
        <div className="claim-heading">
          <div className="badge">STEP 01 / 03</div>
          <h1>Start your vehicle claim</h1>
          <p>Enter the insured vehicle details. These are combined with AI damage analysis in the final claim report.</p>
        </div>

        <form className="claim-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="manufacturer">Manufacturer</label>
            <select id="manufacturer" value={vehicle.manufacturer} onChange={update("manufacturer")}>
              <option value="">Select manufacturer</option>
              {MANUFACTURERS.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="model">Model</label>
            <input id="model" value={vehicle.model} onChange={update("model")} placeholder="e.g. i20" />
          </div>
          <div className="form-group">
            <label htmlFor="year">Manufacturing Year</label>
            <input id="year" type="number" value={vehicle.year} onChange={update("year")} placeholder="e.g. 2021" />
          </div>
          <div className="form-group">
            <label htmlFor="reg">Registration Number</label>
            <input id="reg" value={vehicle.registration_number} onChange={update("registration_number")} placeholder="e.g. KA01AB1234" />
          </div>
          {error && <div className="form-error full-width">{error}</div>}
          <div className="form-footer full-width">
            <span>{vehicle.manufacturer && vehicle.model ? `${vehicle.manufacturer} ${vehicle.model}` : "Vehicle details required"}</span>
            <button type="submit" className="primary-btn">Continue <span>→</span></button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default NewClaim;
