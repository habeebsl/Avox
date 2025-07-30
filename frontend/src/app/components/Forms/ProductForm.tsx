'use client';

import { useEffect } from 'react';
import { useAdRequest } from '@/app/store/adRequestStore';
import { InformationCircleIcon } from '@heroicons/react/24/outline';

const ProductForm = () => {
  const { 
    cta, 
    setCTA, 
    offerSummary, 
    setOfferSummary, 
    productName, 
    setProductName, 
    productSummary, 
    setProductSummary,
    setDisableNextButton
  } = useAdRequest()

  useEffect(() => {
    if (productName && productSummary && offerSummary && cta) {
      setDisableNextButton(false)
    } else {
      setDisableNextButton(true)
    }
  }, [cta, offerSummary, productName, productSummary])

  return (
    <div className="bg-black min-h-screen p-8">
      <div className="max-w-lg mx-auto">
        <div className="bg-black border border-gray-800 rounded-3xl p-8 shadow-2xl backdrop-blur-sm">
          
          {/* Product Name */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-white text-lg font-semibold tracking-wide">Product Name</h3>
              <div className="group relative">
                <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                  Enter your product's official name or title
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                </div>
              </div>
            </div>
            
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="FitPro X1 Smart Fitness Tracker"
              className="w-full bg-gray-800/30 border border-gray-600 rounded-2xl px-5 py-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-gray-400 transition-all duration-200 hover:bg-gray-700/30 hover:border-gray-500"
            />
            <div className="flex justify-between items-center mt-2">
              <div className="text-xs text-gray-500">
                Use your brand and model name
              </div>
              <div className="text-xs text-gray-400">
                {productName.length}/80
              </div>
            </div>
          </div>

          {/* Product Summary */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-white text-lg font-semibold tracking-wide">Product Summary</h3>
              <div className="group relative">
                <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                  Brief description of your product's key features and benefits
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                </div>
              </div>
            </div>
            
            <textarea
              value={productSummary}
              onChange={(e) => setProductSummary(e.target.value)}
              placeholder="Revolutionary fitness tracker with heart rate monitoring, GPS tracking, and 7-day battery life..."
              className="w-full bg-gray-800/30 border border-gray-600 rounded-2xl px-5 py-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-gray-400 transition-all duration-200 hover:bg-gray-700/30 hover:border-gray-500"
              rows={4}
            />
            <div className="flex justify-between items-center mt-2">
              <div className="text-xs text-gray-500">
                Keep it concise and highlight key benefits
              </div>
              <div className="text-xs text-gray-400">
                {productSummary.length}/500
              </div>
            </div>
          </div>

          {/* Offer Summary */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-white text-lg font-semibold tracking-wide">Offer Summary</h3>
              <div className="group relative">
                <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                  Special deals, discounts, or promotional offers available
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                </div>
              </div>
            </div>
            
            <textarea
              value={offerSummary}
              onChange={(e) => setOfferSummary(e.target.value)}
              placeholder="Get 30% off your first order plus free shipping. Limited time offer expires in 7 days..."
              className="w-full bg-gray-800/30 border border-gray-600 rounded-2xl px-5 py-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-gray-400 transition-all duration-200 hover:bg-gray-700/30 hover:border-gray-500"
              rows={3}
            />
            <div className="flex justify-between items-center mt-2">
              <div className="text-xs text-gray-500">
                Highlight urgency and value proposition
              </div>
              <div className="text-xs text-gray-400">
                {offerSummary.length}/300
              </div>
            </div>
          </div>

          {/* Call to Action */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <h3 className="text-white text-lg font-semibold tracking-wide">Call to Action</h3>
              <div className="group relative">
                <InformationCircleIcon className="w-5 h-5 text-gray-500 cursor-help hover:text-gray-400 transition-colors" />
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap z-20 shadow-lg border border-gray-700">
                  Action phrase that encourages immediate customer response
                  <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800"></div>
                </div>
              </div>
            </div>
            
            <textarea
              value={cta}
              onChange={(e) => setCTA(e.target.value)}
              placeholder="Shop Now & Save 30% - Free Shipping Today Only!"
              className="w-full bg-gray-800/30 border border-gray-600 rounded-2xl px-5 py-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-gray-400 transition-all duration-200 hover:bg-gray-700/30 hover:border-gray-500"
              rows={2}
            />
            <div className="flex justify-between items-center mt-2">
              <div className="text-xs text-gray-500">
                Keep it action-oriented and compelling
              </div>
              <div className="text-xs text-gray-400">
                {cta.length}/100
              </div>
            </div>
          </div>

          {/* Form Status Indicator */}
          <div className="bg-gray-800/50 rounded-2xl p-4 border border-gray-700">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-400">
                Form Completion
              </div>
              <div className="flex gap-2">
                <div className={`w-3 h-3 rounded-full transition-all duration-200 ${
                  productName.length > 0 ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-gray-600'
                }`}></div>
                <div className={`w-3 h-3 rounded-full transition-all duration-200 ${
                  productSummary.length > 0 ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-gray-600'
                }`}></div>
                <div className={`w-3 h-3 rounded-full transition-all duration-200 ${
                  offerSummary.length > 0 ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-gray-600'
                }`}></div>
                <div className={`w-3 h-3 rounded-full transition-all duration-200 ${
                  cta.length > 0 ? 'bg-green-400 shadow-lg shadow-green-400/50' : 'bg-gray-600'
                }`}></div>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              {[productName, productSummary, offerSummary, cta].filter(field => field.length > 0).length}/4 fields completed
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default ProductForm;