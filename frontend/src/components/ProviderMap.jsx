import { useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
import providersData from "../data/providers.json";

// Reads accepted providers from src/data/providers.json.
function getRawProviders() {
  if (Array.isArray(providersData)) {
    return providersData;
  }

  if (Array.isArray(providersData.accepted)) {
    return providersData.accepted;
  }

  if (Array.isArray(providersData.providers)) {
    return providersData.providers;
  }

  if (Array.isArray(providersData.data)) {
    return providersData.data;
  }

  if (Array.isArray(providersData.items)) {
    return providersData.items;
  }

  console.warn("Unknown providers.json structure:", providersData);
  return [];
}

// Returns the provider category used for filtering and marker color.
function getCategory(provider) {
  return provider.category || provider.targetCategory || "Unbekannt";
}

// Returns the country code used for country filtering.
function getCountry(provider) {
  return provider.address?.country || provider.searchCountry || "Unbekannt";
}

// Converts country codes into readable labels.
function getCountryLabel(countryCode) {
  if (countryCode === "DE") {
    return "Deutschland";
  }

  if (countryCode === "AT") {
    return "Österreich";
  }

  if (countryCode === "CH") {
    return "Schweiz";
  }

  return countryCode;
}

// Returns the city used for city filtering.
function getCity(provider) {
  return provider.address?.city || provider.searchCity || "Unbekannt";
}

// Returns a readable address string for the sidebar and popup.
function getAddressText(provider) {
  if (typeof provider.address === "string") {
    return provider.address;
  }

  if (provider.address?.formatted) {
    return provider.address.formatted;
  }

  if (provider.address) {
    return [
      provider.address.street,
      provider.address.postalCode,
      provider.address.city,
      provider.address.country,
    ]
      .filter(Boolean)
      .join(", ");
  }

  return "Adresse nicht vorhanden";
}

// Returns a readable service description.
function getServicesText(provider) {
  const category = getCategory(provider);

  if (category === "DEXA") {
    return "DEXA Body Composition Scan";
  }

  if (category === "Blutlabor") {
    return "Bluttest als Selbstzahler";
  }

  return "Leistung nicht angegeben";
}

// Formats optional public price information.
function formatPrice(prices) {
  if (!prices) {
    return "Nicht öffentlich verfügbar";
  }

  if (prices.amount && prices.currency) {
    return `${prices.amount} ${prices.currency}${
      prices.note ? ` – ${prices.note}` : ""
    }`;
  }

  return prices.note || "Nicht öffentlich verfügbar";
}

// Formats the self-payer status.
function formatSelfPayer(value) {
  if (value === "yes" || value === true) {
    return "Ja";
  }

  if (value === "no" || value === false) {
    return "Nein";
  }

  return "k.A.";
}

// Marker colors by provider category.
const markerIcons = {
  DEXA: new L.Icon({
    iconUrl:
      "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
    shadowUrl:
      "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  }),

  Blutlabor: new L.Icon({
    iconUrl:
      "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
    shadowUrl:
      "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  }),
};

function ProviderMap() {
  const [activeFilter, setActiveFilter] = useState("Alle");
  const [activeCountry, setActiveCountry] = useState("Alle");
  const [activeCity, setActiveCity] = useState("Alle");
  const [selectedProviderId, setSelectedProviderId] = useState(null);

  const providers = getRawProviders();

  const providersWithCoordinates = useMemo(() => {
    return providers.filter(
      (provider) =>
        provider.coordinates &&
        typeof provider.coordinates.lat === "number" &&
        typeof provider.coordinates.lng === "number"
    );
  }, [providers]);

  const availableCities = useMemo(() => {
    const cities = providersWithCoordinates
      .filter((provider) => {
        return activeCountry === "Alle" || getCountry(provider) === activeCountry;
      })
      .map((provider) => getCity(provider))
      .filter((city) => city && city !== "Unbekannt");

    return [...new Set(cities)].sort((a, b) => a.localeCompare(b, "de"));
  }, [providersWithCoordinates, activeCountry]);

  const filteredProviders = useMemo(() => {
    return providersWithCoordinates.filter((provider) => {
      const categoryMatches =
        activeFilter === "Alle" || getCategory(provider) === activeFilter;

      const countryMatches =
        activeCountry === "Alle" || getCountry(provider) === activeCountry;

      const cityMatches =
        activeCity === "Alle" || getCity(provider) === activeCity;

      return categoryMatches && countryMatches && cityMatches;
    });
  }, [activeFilter, activeCountry, activeCity, providersWithCoordinates]);

  const selectedProvider = filteredProviders.find(
    (provider) =>
      (provider.id || `${provider.name}-${getAddressText(provider)}`) ===
      selectedProviderId
  );

  const dexaCount = providersWithCoordinates.filter(
    (provider) => getCategory(provider) === "DEXA"
  ).length;

  const bloodLabCount = providersWithCoordinates.filter(
    (provider) => getCategory(provider) === "Blutlabor"
  ).length;

  return (
    <section className="map-section">
      <aside className="sidebar">
        <div className="sidebar-top">
          <h2>Verifizierte Anbieter</h2>

          <p className="result-count">
            {providersWithCoordinates.length} Anbieter insgesamt · {dexaCount}{" "}
            DEXA · {bloodLabCount} Blutlabor
          </p>

          <div className="filter-group">
            <p className="filter-label">Kategorie</p>

            <div className="filter-buttons">
              {["Alle", "DEXA", "Blutlabor"].map((filter) => (
                <button
                  key={filter}
                  className={activeFilter === filter ? "active" : ""}
                  onClick={() => {
                    setActiveFilter(filter);
                    setSelectedProviderId(null);
                  }}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <p className="filter-label">Land</p>

            <div className="filter-buttons country-buttons">
              {[
                { value: "Alle", label: "Alle Länder" },
                { value: "DE", label: "Deutschland" },
                { value: "AT", label: "Österreich" },
                { value: "CH", label: "Schweiz" },
              ].map((country) => (
                <button
                  key={country.value}
                  className={activeCountry === country.value ? "active" : ""}
                  onClick={() => {
                    setActiveCountry(country.value);
                    setActiveCity("Alle");
                    setSelectedProviderId(null);
                  }}
                >
                  {country.label}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <p className="filter-label">Stadt</p>

            <select
              className="city-select"
              value={activeCity}
              onChange={(event) => {
                setActiveCity(event.target.value);
                setSelectedProviderId(null);
              }}
            >
              <option value="Alle">Alle Städte</option>
              {availableCities.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>
          </div>

          <p className="result-count">
            {filteredProviders.length} Anbieter angezeigt
          </p>
        </div>

        <div className="provider-list">
          {filteredProviders.map((provider, index) => {
            const providerId =
              provider.id || `${provider.name}-${getAddressText(provider)}`;
            const category = getCategory(provider);

            return (
              <article
                key={providerId || index}
                className={`provider-card ${
                  selectedProviderId === providerId ? "selected" : ""
                }`}
                onClick={() => setSelectedProviderId(providerId)}
              >
                <div className="badge-row">
                  <span className={`badge ${category.toLowerCase()}`}>
                    {category}
                  </span>
                </div>

                <h3>{provider.name}</h3>

                <p>{getAddressText(provider)}</p>

                <p>
                  <strong>Land:</strong>{" "}
                  {getCountryLabel(getCountry(provider))}
                </p>

                <p>
                  <strong>Stadt:</strong> {getCity(provider)}
                </p>

                <p>
                  <strong>Leistungen:</strong> {getServicesText(provider)}
                </p>

                {selectedProviderId === providerId && (
                  <div className="card-actions">
                    {provider.contact?.website && (
                      <a
                        href={provider.contact.website}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(event) => event.stopPropagation()}
                      >
                        Website öffnen
                      </a>
                    )}

                    {provider.contact?.googleMaps && (
                      <a
                        href={provider.contact.googleMaps}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(event) => event.stopPropagation()}
                      >
                        Google Maps öffnen
                      </a>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>

        {selectedProvider && (
          <div className="details-panel">
            <h2>{selectedProvider.name}</h2>

            <p>
              <strong>Kategorie:</strong> {getCategory(selectedProvider)}
            </p>

            <p>
              <strong>Land:</strong>{" "}
              {getCountryLabel(getCountry(selectedProvider))}
            </p>

            <p>
              <strong>Stadt:</strong> {getCity(selectedProvider)}
            </p>

            <p>
              <strong>Adresse:</strong>
              <br />
              {getAddressText(selectedProvider)}
            </p>

            <p>
              <strong>Leistungen:</strong>
              <br />
              {getServicesText(selectedProvider)}
            </p>

            <p>
              <strong>Selbstzahler möglich:</strong>{" "}
              {formatSelfPayer(selectedProvider.selfPayerPossible)}
            </p>

            {selectedProvider.prices && (
              <p>
                <strong>Preis:</strong>{" "}
                {formatPrice(selectedProvider.prices)}
              </p>
            )}

            {selectedProvider.contact?.phone && (
              <p>
                <strong>Telefon:</strong> {selectedProvider.contact.phone}
              </p>
            )}

            {selectedProvider.contact?.website && (
              <a
                href={selectedProvider.contact.website}
                target="_blank"
                rel="noreferrer"
              >
                Website öffnen
              </a>
            )}

            {selectedProvider.contact?.googleMaps && (
              <a
                href={selectedProvider.contact.googleMaps}
                target="_blank"
                rel="noreferrer"
              >
                Google Maps öffnen
              </a>
            )}
          </div>
        )}
      </aside>

      <div className="map-wrapper">
        <MapContainer
          center={[48.8, 10.4]}
          zoom={6}
          scrollWheelZoom={true}
          className="map"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {filteredProviders.map((provider, index) => {
            const providerId =
              provider.id || `${provider.name}-${getAddressText(provider)}`;
            const category = getCategory(provider);

            return (
              <Marker
                key={providerId || index}
                position={[provider.coordinates.lat, provider.coordinates.lng]}
                icon={markerIcons[category] || markerIcons.DEXA}
                eventHandlers={{
                  click: () => setSelectedProviderId(providerId),
                }}
              >
                <Popup>
                  <div className="popup-content">
                    <h3>{provider.name}</h3>

                    <p>
                      <strong>Kategorie:</strong> {category}
                    </p>

                    <p>
                      <strong>Land:</strong>{" "}
                      {getCountryLabel(getCountry(provider))}
                    </p>

                    <p>
                      <strong>Stadt:</strong> {getCity(provider)}
                    </p>

                    <p>
                      <strong>Leistungen:</strong>
                      <br />
                      {getServicesText(provider)}
                    </p>

                    <p>
                      <strong>Adresse:</strong>
                      <br />
                      {getAddressText(provider)}
                    </p>

                    <p>
                      <strong>Koordinaten:</strong>
                      <br />
                      Lat: {provider.coordinates.lat}, Lng:{" "}
                      {provider.coordinates.lng}
                    </p>

                    <p>
                      <strong>Selbstzahler möglich:</strong>{" "}
                      {formatSelfPayer(provider.selfPayerPossible)}
                    </p>

                    {provider.prices && (
                      <p>
                        <strong>Preis:</strong> {formatPrice(provider.prices)}
                      </p>
                    )}

                    {provider.contact?.phone && (
                      <p>
                        <strong>Telefon:</strong> {provider.contact.phone}
                      </p>
                    )}

                    {provider.contact?.website && (
                      <a
                        href={provider.contact.website}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Website öffnen
                      </a>
                    )}

                    {provider.contact?.googleMaps && (
                      <a
                        href={provider.contact.googleMaps}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Google Maps öffnen
                      </a>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </section>
  );
}

export default ProviderMap;

