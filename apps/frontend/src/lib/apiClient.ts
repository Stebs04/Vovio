import axios from 'axios'

/**
 * Istanza singleton del client Axios per effettuare richieste HTTP al backend.
 * Configurato con le impostazioni predefinite per l'applicazione Vovio.
 */
export const apiClient = axios.create({
    // L'URL di base per l'API.
    // Utilizza la variabile d'ambiente NEXT_PUBLIC_API_URL in produzione/staging,
    // oppure di default localhost:3000 per lo sviluppo locale.
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',

    // Timeout della richiesta in millisecondi.
    // Impostato a 5 minuti (300.000ms) per gestire task lunghi
    // come l'elaborazione video o il caricamento delle trascrizioni.
    timeout: 300000, 
    
    // Header predefiniti per garantire la comunicazione in formato JSON.
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }, 
})
