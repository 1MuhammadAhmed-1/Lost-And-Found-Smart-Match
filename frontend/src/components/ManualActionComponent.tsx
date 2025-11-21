import React, { useState, useEffect } from 'react';

// Define the available manual forms
type ManualFormView = 'dashboard' | 'report' | 'search' | 'claim';

// Type definitions for various data structures
interface ReportFormData {
    name: string;
    description: string;
    found_at: string;
}

interface Item {
    item_id: string; // The UUID provided by the backend
    item_name: string; // Corrected field name to match FoundItemOut schema
    description: string;
    location_found: string; // Corrected field name to match FoundItemOut schema
    date_found: string; // ISO date string
    status: 'PENDING' | 'CLAIMED' | 'RETURNED'; // Added PENDING/RETURNED status
}

interface ClaimFormData {
    item_id: string;
    contact_name: string; // Not used by backend, but kept for UX
    contact_email: string; // Not used by backend, but kept for UX
    details: string; // Not used by backend, but kept for UX
}

const ManualActionComponent: React.FC = () => {
    const [formView, setFormView] = useState<ManualFormView>('dashboard');
    // State to pass the item ID from Search results to the Claim form
    const [claimedItemId, setClaimedItemId] = useState<string>('');

    // Helper function to safely retrieve the token
    const getToken = (): string | null => {
        // Use window.localStorage for robustness
        const token = window.localStorage.getItem('authToken');
        if (!token) {
            console.error("Authentication token not found in localStorage.");
        }
        return token;
    };
    
    // Helper for displaying messages
    const MessageDisplay: React.FC<{ text: string, type: 'success' | 'error' | 'info' }> = ({ text, type }) => (
        <div className={`p-3 rounded-lg text-sm font-medium ${type === 'success' ? 'bg-green-100 text-green-700' : type === 'error' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
            {text}
        </div>
    );
    
    // Function to handle switching to the Claim form and setting the ID
    const navigateToClaim = (itemId: string = '') => {
        setClaimedItemId(itemId);
        setFormView('claim');
    };
    
    // -------------------------------------------------------------
    // --- 1. REPORT FOUND ITEM FORM -------------------------------
    // -------------------------------------------------------------

    const ReportForm: React.FC = () => {
        // Frontend form fields use 'name', 'description', 'found_at'. 
        // Backend uses FoundItemIn: 'item_name', 'description', 'location_found', 'contact_email'
        const [formData, setFormData] = useState<ReportFormData & { contact_email: string }>({ 
            name: '', description: '', found_at: '', contact_email: '' 
        });
        const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' | 'info' }>({ text: '', type: 'info' });
        const [isLoading, setIsLoading] = useState(false);

        const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
            setFormData({ ...formData, [e.target.name]: e.target.value });
        };

        const handleSubmit = async (e: React.FormEvent) => {
            e.preventDefault();
            setIsLoading(true);
            setMessage({ text: '', type: 'info' });

            // FIX: getToken is called just before submission, ensuring it's fresh. (Already correct)
            const token = getToken(); 
            if (!token) {
                setMessage({ text: 'Error: Not authenticated. Please log in.', type: 'error' });
                setIsLoading(false);
                return;
            }

            try {
                // *** FIX 1: URL path corrected for Django Ninja (using proxy path /api/core/found_items/) ***
                const response = await fetch('/api/core/found_items/', { 
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json', 
                        // The crucial fix: sending the token in the Authorization header
                        'Authorization': `Token ${token}` 
                    },
                    body: JSON.stringify({
                        item_name: formData.name, // Mapping frontend 'name' to backend 'item_name'
                        description: formData.description,
                        location_found: formData.found_at, // Mapping frontend 'found_at' to backend 'location_found'
                        contact_email: formData.contact_email,
                    }),
                });

                // Check if response.ok is false *before* attempting to parse JSON, as error bodies can be non-JSON
                const data = await response.json().catch(() => ({ detail: 'Unknown error occurred or server returned non-JSON data.' })); 

                if (response.ok) {
                    setMessage({ 
                        text: `Success! Item reported. Item ID: ${data.item_id}.`, 
                        type: 'success' 
                    });
                    setFormData({ name: '', description: '', found_at: '', contact_email: '' });
                } else {
                    // Check if data has a specific detail field for error message (Django Ninja standard)
                    const errorDetails = data.detail || data.message || JSON.stringify(data);
                    // Add check for common Authorization errors
                    if (response.status === 401) {
                        setMessage({ text: 'Failed to report item: Unauthorized. Please log out and log back in.', type: 'error' });
                    } else if (response.status === 404) {
                        // Explicit 404 check for the common routing issue
                        setMessage({ text: 'Failed to report item: Endpoint not found (404). Check API path.', type: 'error' });
                    } else {
                        setMessage({ text: `Failed to report item: ${errorDetails}`, type: 'error' });
                    }
                }
            } catch (error) {
                console.error('Network or fetch error during Report:', error);
                // REFINED ERROR MESSAGE HERE
                setMessage({ 
                    text: 'A network error occurred. Please check your connection or log out and back in to refresh your session.', 
                    type: 'error' 
                });
            } finally {
                setIsLoading(false);
            }
        };

        return (
            <div className="p-8 bg-white rounded-xl shadow-2xl max-w-xl mx-auto">
                <h3 className="text-2xl font-bold mb-6 text-gray-800">Report Found Item</h3>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700">Item Name:</label>
                        <input
                            id="name" name="name" type="text" value={formData.name} onChange={handleChange} required
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                        />
                    </div>
                    
                    <div>
                        <label htmlFor="description" className="block text-sm font-medium text-gray-700">Description (Color, brand, distinguishing marks):</label>
                        <textarea
                            id="description" name="description" value={formData.description} onChange={handleChange} required rows={3}
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 resize-none"
                        ></textarea>
                    </div>

                    <div>
                        <label htmlFor="found_at" className="block text-sm font-medium text-gray-700">Location Found:</label>
                        <input
                            id="found_at" name="found_at" type="text" value={formData.found_at} onChange={handleChange} required
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                        />
                    </div>

                    <div>
                        <label htmlFor="contact_email" className="block text-sm font-medium text-gray-700">Your Contact Email:</label>
                        <input
                            id="contact_email" name="contact_email" type="email" value={formData.contact_email} onChange={handleChange} required
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500"
                        />
                    </div>
                    
                    {message.text && <MessageDisplay text={message.text} type={message.type} />}

                    <div className="flex justify-between items-center pt-4">
                        <button type="button" onClick={() => setFormView('dashboard')} className="text-gray-600 hover:text-gray-800 font-medium p-2 transition duration-150">
                            ← Back to Dashboard
                        </button>
                        <button 
                            type="submit" disabled={isLoading}
                            className={`px-6 py-3 rounded-lg text-white font-semibold transition duration-150 ${isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'}`}
                        >
                            {isLoading ? 'Submitting...' : 'Report Item'}
                        </button>
                    </div>
                </form>
            </div>
        );
    };

    // -------------------------------------------------------------
    // --- 2. SEARCH LOST ITEM FORM --------------------------------
    // -------------------------------------------------------------

    const SearchForm: React.FC = () => {
        const [keywords, setKeywords] = useState('');
        const [locationHint, setLocationHint] = useState('');
        const [results, setResults] = useState<Item[] | null>(null);
        const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' | 'info' }>({ text: '', type: 'info' });
        const [isLoading, setIsLoading] = useState(false);

        const handleSubmit = async (e: React.FormEvent) => {
            e.preventDefault();
            setIsLoading(true);
            setResults(null);
            setMessage({ text: '', type: 'info' });

            const token = getToken();
            if (!token) {
                setMessage({ text: 'Error: Not authenticated. Please log in.', type: 'error' });
                setIsLoading(false);
                return;
            }
            
            // FIX 2: Correct search endpoint to use the correct proxy path /api/core/search/
            const searchEndpoint = `/api/core/search/?keywords=${encodeURIComponent(keywords.trim())}&location_hint=${encodeURIComponent(locationHint.trim())}`; 

            try {
                const response = await fetch(searchEndpoint, {
                    method: 'GET', // Search is typically a GET request with query params
                    // The crucial fix: sending the token in the Authorization header
                    headers: { 'Authorization': `Token ${token}` }, 
                });

                const data: Item[] | { detail: string } = await response.json().catch(() => ({ detail: 'Unknown error occurred or server returned non-JSON data.' }));

                if (response.ok) {
                    setResults(data as Item[]); // Cast since we expect Item[] on success
                    if ((data as Item[]).length > 0) {
                            setMessage({ text: `${(data as Item[]).length} potential matches found.`, type: 'success' });
                    } else {
                        setMessage({ text: 'No matches found based on your criteria.', type: 'info' });
                    }
                } else {
                    const errorDetails = (data as { detail: string }).detail || JSON.stringify(data);
                    // Add check for common Authorization errors
                    if (response.status === 401) {
                         setMessage({ text: 'Search failed: Unauthorized. Please log out and log back in.', type: 'error' });
                    } else {
                        setMessage({ text: `Search failed: ${errorDetails}`, type: 'error' });
                    }
                }
            } catch (error) {
                console.error('Network or fetch error during Search:', error);
                setMessage({ text: 'A network error occurred during search. Please check your connection or log out and back in.', type: 'error' });
            } finally {
                setIsLoading(false);
            }
        };

        return (
            <div className="p-8 bg-white rounded-xl shadow-2xl max-w-2xl mx-auto">
                <h3 className="text-2xl font-bold mb-6 text-gray-800">Search Lost Item Database</h3>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="keywords" className="block text-sm font-medium text-gray-700">Keywords (Required):</label>
                        <input
                            id="keywords" name="keywords" type="text" value={keywords} onChange={(e) => setKeywords(e.target.value)} 
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                            placeholder="e.g., wallet, red, leather, backpack"
                            required
                        />
                    </div>
                    <div>
                        <label htmlFor="locationHint" className="block text-sm font-medium text-gray-700">Location Hint (Optional):</label>
                        <input
                            id="locationHint" name="locationHint" type="text" value={locationHint} onChange={(e) => setLocationHint(e.target.value)} 
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                            placeholder="e.g., cafeteria, locker room"
                        />
                    </div>

                    {message.text && <MessageDisplay text={message.text} type={message.type} />}

                    <div className="flex justify-between items-center pt-4">
                        <button type="button" onClick={() => setFormView('dashboard')} className="text-gray-600 hover:text-gray-800 font-medium p-2 transition duration-150">
                            ← Back to Dashboard
                        </button>
                        <button 
                            type="submit" disabled={isLoading}
                            className={`px-6 py-3 rounded-lg text-white font-semibold transition duration-150 ${isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                        >
                            {isLoading ? 'Searching...' : 'Search Items'}
                        </button>
                    </div>
                </form>

                {/* Search Results Display */}
                {results && (
                    <div className="mt-8 pt-4 border-t border-gray-200">
                        <h4 className="text-xl font-bold mb-4 text-gray-800">Search Results ({results.length})</h4>
                        <div className="space-y-4">
                            {results.length > 0 ? (
                                results.map((item) => (
                                    <div key={item.item_id} className="p-4 border border-gray-100 rounded-lg bg-gray-50 text-left shadow-sm">
                                        <p className="font-bold text-lg text-blue-700">{item.item_name}</p>
                                        <p className="text-sm text-gray-600">ID: <span className="font-mono text-xs">{item.item_id}</span></p>
                                        <p className="text-sm">Found At: {item.location_found}</p>
                                        <p className="text-sm">Status: <span className={`font-semibold ${item.status === 'CLAIMED' ? 'text-red-500' : 'text-green-500'}`}>{item.status}</span></p>
                                        <p className="mt-2 text-sm italic">{item.description}</p>
                                        {/* Button uses navigateToClaim to pre-fill the ID */}
                                        <button 
                                            onClick={() => navigateToClaim(item.item_id)}
                                            disabled={item.status !== 'PENDING'}
                                            className={`mt-2 px-3 py-1 text-xs rounded-full transition ${item.status === 'PENDING' ? 'bg-yellow-500 text-white hover:bg-yellow-600' : 'bg-gray-300 text-gray-600 cursor-not-allowed'}`}
                                        >
                                            {item.status === 'PENDING' ? 'Initiate Claim' : 'Already Claimed/Returned'}
                                        </button>
                                    </div>
                                ))
                            ) : (
                                <p className="text-gray-500 italic">No items matched your search criteria.</p>
                            )}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    // -------------------------------------------------------------
    // --- 3. CLAIM ITEM FORM --------------------------------------
    // -------------------------------------------------------------

    const ClaimForm: React.FC = () => {
        // Initialize state to use claimedItemId if it exists, otherwise empty
        const [formData, setFormData] = useState<ClaimFormData>({
            item_id: claimedItemId || '', // Use the ID passed from search
            contact_name: '',
            contact_email: '',
            details: '',
        });
        const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' | 'info' }>({ text: '', type: 'info' });
        const [isLoading, setIsLoading] = useState(false);

        const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
            setFormData({ ...formData, [e.target.name]: e.target.value });
        };

        const handleSubmit = async (e: React.FormEvent) => {
            e.preventDefault();
            setIsLoading(true);
            setMessage({ text: '', type: 'info' });

            const token = getToken();
            if (!token) {
                setMessage({ text: 'Error: Not authenticated. Please log in.', type: 'error' });
                setIsLoading(false);
                return;
            }
            
            // Ensure ID is provided
            if (!formData.item_id.trim()) {
                setMessage({ text: 'Please enter a valid Item ID.', type: 'error' });
                setIsLoading(false);
                return;
            }

            try {
                // FIX 3: Correct URL to pass the item_id as a path parameter with correct proxy path /api/core/claim_item/
                const response = await fetch(`/api/core/claim_item/${formData.item_id}`, { 
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json', 
                        'Authorization': `Token ${token}` // The crucial fix
                    },
                    // The Claim endpoint expects an empty body in the current backend spec
                    body: JSON.stringify({}), 
                });

                const data = await response.json().catch(() => ({ detail: 'Unknown error occurred or server returned non-JSON data.' }));

                if (response.ok) {
                    setMessage({ 
                        text: `Claim initiated successfully for Item ID ${formData.item_id}. The item is now marked as CLAIMED.`, 
                        type: 'success' 
                    });
                    // Reset form fields after successful submission, and clear the temporary claimedItemId state
                    setFormData(prev => ({ ...prev, contact_name: '', contact_email: '', details: '' }));
                    setClaimedItemId(''); // Clear the pre-filled state
                } else {
                    // Check if the error is due to the item already being claimed/not found
                    const errorDetails = data.detail || data.message || JSON.stringify(data);
                    // Add check for common Authorization errors
                    if (response.status === 401) {
                           setMessage({ text: 'Claim failed: Unauthorized. Please log out and log back in.', type: 'error' });
                    } else {
                        setMessage({ text: `Claim failed: ${errorDetails}`, type: 'error' });
                    }
                }
            } catch (error) {
                // This catch block handles generic network failures
                console.error('Network or fetch error during Claim:', error);
                setMessage({ text: 'A network error occurred during claim. Please check your connection or log out and back in.', type: 'error' });
            } finally {
                setIsLoading(false);
            }
        };
        
        // This useEffect is where the ESLint warning was (Line 385:12)
        // We keep this dependency as it is correct for the logic
        useEffect(() => {
            if (claimedItemId) {
                setFormData(prev => ({ ...prev, item_id: claimedItemId }));
            }
        }, [claimedItemId]);

        return (
            <div className="p-8 bg-white rounded-xl shadow-2xl max-w-xl mx-auto">
                <h3 className="text-2xl font-bold mb-6 text-gray-800">Claim Item by ID</h3>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="item_id" className="block text-sm font-medium text-gray-700">Item ID (UUID of the Found Item):</label>
                        <input
                            id="item_id" name="item_id" type="text" value={formData.item_id} onChange={handleChange} required
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-yellow-500 focus:border-yellow-500"
                            placeholder="e.g., 550e8400-e29b-41d4-a716-446655440000"
                            // If the ID was pre-filled, make it read-only
                            readOnly={!!claimedItemId} 
                        />
                        {claimedItemId && <p className="text-xs text-green-600 mt-1">Item ID pre-filled from search results.</p>}
                    </div>
                    {/* These fields are cosmetic since the backend only uses the ID in the URL for the Claim endpoint, but they are good for user context */}
                    <div>
                        <label htmlFor="contact_name" className="block text-sm font-medium text-gray-700">Your Name:</label>
                        <input
                            id="contact_name" name="contact_name" type="text" value={formData.contact_name} onChange={handleChange} required
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label htmlFor="contact_email" className="block text-sm font-medium text-gray-700">Your Email:</label>
                        <input
                            id="contact_email" name="contact_email" type="email" value={formData.contact_email} onChange={handleChange} required
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label htmlFor="details" className="block text-sm font-medium text-gray-700">Details proving ownership:</label>
                        <textarea
                            id="details" name="details" value={formData.details} onChange={handleChange} required rows={3}
                            className="w-full mt-1 p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 resize-none"
                            placeholder="e.g., The phone has a crack on the top left corner, and the wallpaper is a dog."
                        ></textarea>
                    </div>
                    
                    {message.text && <MessageDisplay text={message.text} type={message.type} />}

                    <div className="flex justify-between items-center pt-4">
                        <button type="button" onClick={() => {setFormView('dashboard'); setClaimedItemId('');}} className="text-gray-600 hover:text-gray-800 font-medium p-2 transition duration-150">
                            ← Back to Dashboard
                        </button>
                        <button 
                            type="submit" disabled={isLoading}
                            className={`px-6 py-3 rounded-lg text-white font-semibold transition duration-150 ${isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-yellow-600 hover:bg-yellow-700'}`}
                        >
                            {isLoading ? 'Submitting Claim...' : 'Submit Claim'}
                        </button>
                    </div>
                </form>
            </div>
        );
    };


    // -------------------------------------------------------------
    // --- 4. DASHBOARD & RENDERING LOGIC ----------------------------
    // -------------------------------------------------------------

    const Dashboard = () => (
        <div className="p-8 bg-white rounded-xl shadow-2xl max-w-lg mx-auto">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">What Manual Action Do You Need?</h2>
            <p className="text-gray-600 mb-6">Use these forms for direct database interaction without the AI Assistant.</p>
            <div className="flex flex-col space-y-4">
                <ActionButton 
                    label="Report a Found Item" 
                    icon="➕" 
                    description="Submit a detailed entry for an item you have found."
                    onClick={() => setFormView('report')}
                    color="bg-green-500 hover:bg-green-600"
                />
                <ActionButton 
                    label="Search for a Lost Item" 
                    icon="🔍" 
                    description="Use specific criteria (keywords, location) to search the database."
                    onClick={() => setFormView('search')}
                    color="bg-blue-500 hover:bg-blue-600"
                />
                <ActionButton 
                    label="Claim an Item by ID" 
                    icon="🆔" 
                    description="Enter a known Item ID or use one from search results."
                    onClick={() => navigateToClaim('')}
                    color="bg-yellow-500 hover:bg-yellow-600"
                />
            </div>
            <p className="mt-6 text-sm text-gray-500">
                You can always return to the "Talk to Assistant" view for guided help.
            </p>
        </div>
    );

    const ActionButton: React.FC<{ label: string, icon: string, description: string, onClick: () => void, color: string }> = ({ label, icon, description, onClick, color }) => (
        <button 
            onClick={onClick}
            className={`flex items-center text-left p-4 rounded-lg text-white transition duration-200 ease-in-out ${color} shadow-lg w-full`}
        >
            <span className="text-3xl mr-4">{icon}</span>
            <div>
                <div className="text-lg font-semibold">{label}</div>
                <div className="text-sm opacity-90">{description}</div>
            </div>
        </button>
    );

    // Render the appropriate component based on the formView state
    const renderForm = () => {
        switch (formView) {
            case 'report':
                return <ReportForm />;
            case 'search':
                return <SearchForm />; 
            case 'claim':
                return <ClaimForm />;
            case 'dashboard':
            default:
                return <Dashboard />;
        }
    };

    return (
        <div className="p-4 min-h-screen bg-gray-50">
            {renderForm()}
        </div>
    );
};

export default ManualActionComponent;