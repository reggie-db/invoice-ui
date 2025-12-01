export interface Invoice {
  lineItems: LineItem[];
  shipTo: ShipTo;
  invoice: InvoiceDetails;
  buyer: Party;
  seller: Party;
  totals: Totals;
}

export interface LineItem {
  description: string;
  serialNumbers: string[];
  lineNumber: string;
  quantityShipped: number;
  manufacturerPartNumber: string;
  unitPrice: number;
  extendedPrice: number;
  quantityOrdered: number;
}

export interface ShipTo {
  name: string;
  attention: string;
  address: string[];
}

export interface InvoiceDetails {
  amountDue: {
    currency: string;
    value: number;
  };
  invoiceNumber: string;
  invoiceDate: string;
  purchaseOrderNumber: string;
  dueDate: string | null;
  salesOrderNumber: string;
  terms: string;
}

export interface Party {
  name: string;
  address: string[];
}

export interface Totals {
  tax: number;
  total: number;
  currency: string;
  subtotal: number;
  shipping: number;
}
