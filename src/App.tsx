import { useState } from "react";
import { InvoiceSearch } from "./components/invoice-search";
import { InvoiceResults } from "./components/invoice-results";
import { mockInvoices } from "./data/mock-invoices";

export default function App() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredInvoices, setFilteredInvoices] = useState(mockInvoices);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    
    if (!query.trim()) {
      setFilteredInvoices(mockInvoices);
      return;
    }

    const lowerQuery = query.toLowerCase();
    const filtered = mockInvoices.filter((invoice) => {
      // Search across multiple fields
      const searchFields = [
        invoice.invoice.invoiceNumber,
        invoice.invoice.purchaseOrderNumber,
        invoice.invoice.salesOrderNumber,
        invoice.shipTo.name,
        invoice.buyer.name,
        invoice.seller.name,
        ...invoice.lineItems.flatMap(item => [
          item.description,
          item.manufacturerPartNumber,
          ...item.serialNumbers
        ])
      ].map(field => field?.toLowerCase() || "");

      return searchFields.some(field => field.includes(lowerQuery));
    });

    setFilteredInvoices(filtered);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-slate-900 mb-2">Hardware Invoice Search</h1>
          <p className="text-slate-600">
            Search through computer hardware orders and invoices
          </p>
        </div>

        <InvoiceSearch onSearch={handleSearch} searchQuery={searchQuery} />

        <InvoiceResults 
          invoices={filteredInvoices} 
          searchQuery={searchQuery}
        />
      </div>
    </div>
  );
}
