import { Search } from "lucide-react";
import { Input } from "./ui/input";

interface InvoiceSearchProps {
  onSearch: (query: string) => void;
  searchQuery: string;
}

export function InvoiceSearch({ onSearch, searchQuery }: InvoiceSearchProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6 mb-6">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 size-5" />
        <Input
          type="text"
          placeholder="Search by invoice number, PO number, serial number, company name..."
          value={searchQuery}
          onChange={(e) => onSearch(e.target.value)}
          className="pl-10 h-12"
        />
      </div>
    </div>
  );
}
