import { InvoiceCard } from "./invoice-card";
import { Invoice } from "../types/invoice";
import { FileX } from "lucide-react";

interface InvoiceResultsProps {
  invoices: Invoice[];
  searchQuery: string;
}

export function InvoiceResults({ invoices, searchQuery }: InvoiceResultsProps) {
  if (invoices.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-12 text-center">
        <FileX className="size-12 text-slate-300 mx-auto mb-4" />
        <h3 className="text-slate-900 mb-2">No invoices found</h3>
        <p className="text-slate-600">
          {searchQuery
            ? `No results match "${searchQuery}". Try a different search term.`
            : "No invoices available."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-slate-600">
          {invoices.length} {invoices.length === 1 ? "invoice" : "invoices"} found
          {searchQuery && ` for "${searchQuery}"`}
        </p>
      </div>

      <div className="space-y-4">
        {invoices.map((invoice) => (
          <InvoiceCard key={invoice.invoice.invoiceNumber} invoice={invoice} />
        ))}
      </div>
    </div>
  );
}
