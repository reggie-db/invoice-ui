import { FileText, Download, Package, MapPin, Building2, Calendar, DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Invoice } from "../types/invoice";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "./ui/collapsible";
import { useState } from "react";

interface InvoiceCardProps {
  invoice: Invoice;
}

export function InvoiceCard({ invoice }: InvoiceCardProps) {
  const [isOpen, setIsOpen] = useState(false);

  const formatCurrency = (value: number, currency: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
    }).format(value);
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <FileText className="size-5 text-slate-600" />
              <h3 className="text-slate-900">Invoice #{invoice.invoice.invoiceNumber}</h3>
            </div>
            <div className="flex flex-wrap gap-4 text-slate-600">
              <div className="flex items-center gap-1.5">
                <Calendar className="size-4" />
                <span>{formatDate(invoice.invoice.invoiceDate)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <DollarSign className="size-4" />
                <span>{formatCurrency(invoice.invoice.amountDue.value, invoice.invoice.amountDue.currency)}</span>
              </div>
              <Badge variant="secondary">{invoice.invoice.terms}</Badge>
            </div>
          </div>
          <Button variant="default" className="gap-2">
            <Download className="size-4" />
            Download PDF
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Order Details */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
          <div>
            <p className="text-slate-500 mb-1">Purchase Order</p>
            <p className="text-slate-900">{invoice.invoice.purchaseOrderNumber}</p>
          </div>
          <div>
            <p className="text-slate-500 mb-1">Sales Order</p>
            <p className="text-slate-900">{invoice.invoice.salesOrderNumber}</p>
          </div>
          <div>
            <p className="text-slate-500 mb-1">Due Date</p>
            <p className="text-slate-900">
              {invoice.invoice.dueDate ? formatDate(invoice.invoice.dueDate) : "N/A"}
            </p>
          </div>
        </div>

        {/* Parties */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex gap-3">
            <Building2 className="size-5 text-slate-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-slate-500 mb-1">Seller</p>
              <p className="text-slate-900">{invoice.seller.name}</p>
              {invoice.seller.address.map((line, idx) => (
                <p key={idx} className="text-slate-600">{line}</p>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <Building2 className="size-5 text-slate-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-slate-500 mb-1">Buyer</p>
              <p className="text-slate-900">{invoice.buyer.name}</p>
              {invoice.buyer.address.map((line, idx) => (
                <p key={idx} className="text-slate-600">{line}</p>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <MapPin className="size-5 text-slate-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-slate-500 mb-1">Ship To</p>
              <p className="text-slate-900">{invoice.shipTo.name}</p>
              <p className="text-slate-600">Attn: {invoice.shipTo.attention}</p>
              {invoice.shipTo.address.map((line, idx) => (
                <p key={idx} className="text-slate-600">{line}</p>
              ))}
            </div>
          </div>
        </div>

        <Separator />

        {/* Line Items */}
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Package className="size-5 text-slate-600" />
              <h4 className="text-slate-900">
                Line Items ({invoice.lineItems.length})
              </h4>
            </div>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm">
                {isOpen ? "Hide Details" : "Show Details"}
              </Button>
            </CollapsibleTrigger>
          </div>

          <CollapsibleContent className="mt-4 space-y-4">
            {invoice.lineItems.map((item, idx) => (
              <div key={idx} className="border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="text-slate-900 mb-2">{item.description}</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-slate-600">
                      <div>
                        <p className="text-slate-500">Line #</p>
                        <p>{item.lineNumber}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">MFR Part #</p>
                        <p>{item.manufacturerPartNumber}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Quantity</p>
                        <p>{item.quantityShipped} / {item.quantityOrdered}</p>
                      </div>
                      <div>
                        <p className="text-slate-500">Unit Price</p>
                        <p>{formatCurrency(item.unitPrice, invoice.totals.currency)}</p>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-slate-500 mb-1">Extended Price</p>
                    <p className="text-slate-900">
                      {formatCurrency(item.extendedPrice, invoice.totals.currency)}
                    </p>
                  </div>
                </div>

                {item.serialNumbers.length > 0 && (
                  <div>
                    <p className="text-slate-500 mb-2">Serial Numbers ({item.serialNumbers.length})</p>
                    <div className="flex flex-wrap gap-2">
                      {item.serialNumbers.map((sn, snIdx) => (
                        <Badge key={snIdx} variant="outline" className="font-mono">
                          {sn}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>

        <Separator />

        {/* Totals */}
        <div className="flex justify-end">
          <div className="w-full md:w-80 space-y-2">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal</span>
              <span>{formatCurrency(invoice.totals.subtotal, invoice.totals.currency)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Shipping</span>
              <span>{formatCurrency(invoice.totals.shipping, invoice.totals.currency)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Tax</span>
              <span>{formatCurrency(invoice.totals.tax, invoice.totals.currency)}</span>
            </div>
            <Separator />
            <div className="flex justify-between text-slate-900">
              <span>Total</span>
              <span>{formatCurrency(invoice.totals.total, invoice.totals.currency)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
