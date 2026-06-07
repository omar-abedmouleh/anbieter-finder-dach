import ProviderMap from "./components/ProviderMap";

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Anbieter-Finder DACH</h1>
          <p>
            Interaktive Karte für verifizierte DEXA Body Composition Anbieter
            und Blutlabore für Selbstzahler.
          </p>
        </div>
      </header>

      <main>
        <ProviderMap />
      </main>
    </div>
  );
}

export default App;
