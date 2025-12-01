import { Invoice } from "../types/invoice";

export const mockInvoices: Invoice[] = [
  {
    lineItems: [
      {
        description: "Dell Pro Max 14 MC14250 / CTO / U5 235H / 16GB / 512GB / Win Hardware Hardware",
        serialNumbers: [
          "26TXFC4",
          "36TXFC",
          "46TXFC4",
          "H5TXFC4",
          "J5TXFC4",
          "H0TXFC4",
          "B1TXFC4",
          "B0TXFC4",
          "C1TXFC4",
          "J0TXFC4",
          "61TXFC4",
          "F1TXFC4",
          "D0TXFC4",
          "21TXFC4",
          "11TXFC4",
          "70TXFC4",
          "C0TXFC4",
          "91TXFC4",
          "51TXFC4",
          "71TXFC4",
          "F0TXFC4",
          "60TXFC4",
          "81TXFC4",
          "41TXFC4",
          "31TXFC4",
          "G0TXFC4",
          "90TXFC4",
          "80TXFC4",
          "D1TXFC4"
        ],
        lineNumber: "50596248",
        quantityShipped: 30,
        manufacturerPartNumber: "3000193484687.1",
        unitPrice: 1168,
        extendedPrice: 35054,
        quantityOrdered: 30
      }
    ],
    shipTo: {
      name: "IRB Holding Corp.",
      attention: "Neil Hathaway",
      address: [
        "130 Royall St",
        "Canton, MA 02021",
        "USA"
      ]
    },
    invoice: {
      amountDue: {
        currency: "USD",
        value: 37550.34
      },
      invoiceNumber: "B20277431",
      invoiceDate: "2025-09-22",
      purchaseOrderNumber: "FRA1000791",
      dueDate: null,
      salesOrderNumber: "S61723476",
      terms: "NET 60"
    },
    buyer: {
      name: "IRB Holding Corp.",
      address: [
        "Three Glenlake Parkway NE",
        "Atlanta, GA 30328",
        "USA"
      ]
    },
    seller: {
      name: "SHI International Corp",
      address: [
        "290 Davidson Ave.",
        "Somerset, NJ 08873"
      ]
    },
    totals: {
      tax: 2190.9,
      total: 37550.34,
      currency: "USD",
      subtotal: 35054,
      shipping: 305
    }
  },
  {
    lineItems: [
      {
        description: "HP EliteBook 840 G9 / Intel Core i7-1265U / 32GB RAM / 1TB SSD / Windows 11 Pro",
        serialNumbers: [
          "5CD3421PQR",
          "5CD3421PQS",
          "5CD3421PQT",
          "5CD3421PQU",
          "5CD3421PQV",
          "5CD3421PQW",
          "5CD3421PQX",
          "5CD3421PQY",
          "5CD3421PQZ",
          "5CD3421PR0"
        ],
        lineNumber: "50596301",
        quantityShipped: 10,
        manufacturerPartNumber: "6C8A4UT#ABA",
        unitPrice: 1849,
        extendedPrice: 18490,
        quantityOrdered: 10
      },
      {
        description: "HP USB-C Dock G5 / 5-in-1 / Power Delivery 100W",
        serialNumbers: [
          "CN412KL001",
          "CN412KL002",
          "CN412KL003",
          "CN412KL004",
          "CN412KL005",
          "CN412KL006",
          "CN412KL007",
          "CN412KL008",
          "CN412KL009",
          "CN412KL010"
        ],
        lineNumber: "50596302",
        quantityShipped: 10,
        manufacturerPartNumber: "5TW10AA#ABA",
        unitPrice: 249,
        extendedPrice: 2490,
        quantityOrdered: 10
      }
    ],
    shipTo: {
      name: "TechFlow Solutions Inc.",
      attention: "Sarah Mitchell",
      address: [
        "2500 Park Avenue",
        "Suite 300",
        "Chicago, IL 60614",
        "USA"
      ]
    },
    invoice: {
      amountDue: {
        currency: "USD",
        value: 22474.8
      },
      invoiceNumber: "B20277589",
      invoiceDate: "2025-10-05",
      purchaseOrderNumber: "TFS2025-1842",
      dueDate: "2025-12-04",
      salesOrderNumber: "S61724012",
      terms: "NET 60"
    },
    buyer: {
      name: "TechFlow Solutions Inc.",
      address: [
        "2500 Park Avenue",
        "Chicago, IL 60614",
        "USA"
      ]
    },
    seller: {
      name: "SHI International Corp",
      address: [
        "290 Davidson Ave.",
        "Somerset, NJ 08873"
      ]
    },
    totals: {
      tax: 1684.8,
      total: 22474.8,
      currency: "USD",
      subtotal: 20980,
      shipping: 0
    }
  },
  {
    lineItems: [
      {
        description: "Lenovo ThinkPad X1 Carbon Gen 11 / Intel Core i7-1355U / 16GB RAM / 512GB SSD",
        serialNumbers: [
          "PF4M2XY9",
          "PF4M2XYA",
          "PF4M2XYB",
          "PF4M2XYC",
          "PF4M2XYD"
        ],
        lineNumber: "50596450",
        quantityShipped: 5,
        manufacturerPartNumber: "21HM002UUS",
        unitPrice: 1629,
        extendedPrice: 8145,
        quantityOrdered: 5
      }
    ],
    shipTo: {
      name: "Nexus Digital Corp",
      attention: "Mike Chen",
      address: [
        "1200 Tech Blvd",
        "San Jose, CA 95110",
        "USA"
      ]
    },
    invoice: {
      amountDue: {
        currency: "USD",
        value: 8776.95
      },
      invoiceNumber: "B20278102",
      invoiceDate: "2025-10-12",
      purchaseOrderNumber: "NDC-2025-Q4-089",
      dueDate: "2025-11-11",
      salesOrderNumber: "S61724568",
      terms: "NET 30"
    },
    buyer: {
      name: "Nexus Digital Corp",
      address: [
        "1200 Tech Blvd",
        "San Jose, CA 95110",
        "USA"
      ]
    },
    seller: {
      name: "SHI International Corp",
      address: [
        "290 Davidson Ave.",
        "Somerset, NJ 08873"
      ]
    },
    totals: {
      tax: 631.95,
      total: 8776.95,
      currency: "USD",
      subtotal: 8145,
      shipping: 0
    }
  },
  {
    lineItems: [
      {
        description: "Apple MacBook Pro 16-inch / M3 Pro / 36GB / 512GB SSD / Space Black",
        serialNumbers: [
          "C02ZK0XTMD6T",
          "C02ZK0XTMD6U",
          "C02ZK0XTMD6V",
          "C02ZK0XTMD6W",
          "C02ZK0XTMD6X",
          "C02ZK0XTMD6Y",
          "C02ZK0XTMD6Z",
          "C02ZK0XTMD70"
        ],
        lineNumber: "50596712",
        quantityShipped: 8,
        manufacturerPartNumber: "MRW13LL/A",
        unitPrice: 2899,
        extendedPrice: 23192,
        quantityOrdered: 8
      },
      {
        description: "AppleCare+ for MacBook Pro 16-inch / 3 Year Coverage",
        serialNumbers: [],
        lineNumber: "50596713",
        quantityShipped: 8,
        manufacturerPartNumber: "S4575LL/A",
        unitPrice: 379,
        extendedPrice: 3032,
        quantityOrdered: 8
      }
    ],
    shipTo: {
      name: "Creative Studios LA",
      attention: "Jennifer Rodriguez",
      address: [
        "8500 Sunset Blvd",
        "West Hollywood, CA 90069",
        "USA"
      ]
    },
    invoice: {
      amountDue: {
        currency: "USD",
        value: 28245.36
      },
      invoiceNumber: "B20278543",
      invoiceDate: "2025-10-18",
      purchaseOrderNumber: "CSLA-OCT-2025-455",
      dueDate: "2025-12-17",
      salesOrderNumber: "S61725234",
      terms: "NET 60"
    },
    buyer: {
      name: "Creative Studios LA",
      address: [
        "8500 Sunset Blvd",
        "West Hollywood, CA 90069",
        "USA"
      ]
    },
    seller: {
      name: "SHI International Corp",
      address: [
        "290 Davidson Ave.",
        "Somerset, NJ 08873"
      ]
    },
    totals: {
      tax: 2421.36,
      total: 28245.36,
      currency: "USD",
      subtotal: 26224,
      shipping: 0
    }
  }
];
