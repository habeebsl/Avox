import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL

const apiClient = axios.create({
	baseURL: `${BASE_URL}/api`,
	headers: {
		'Content-Type': 'application/json'
	}
})

export const apiService = {
    createReservation() {
        return apiClient.post("/clones/reservations/create")
    },

    getVoiceTrainingSents(languageCode: string) {
        return apiClient.get("/clones/sentences", {
            params: {
                language_code: languageCode
            }
        })
    }
}