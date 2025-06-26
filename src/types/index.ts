export interface Reel {
  id: string;
  shortcode: string;
  url: string;
  username: string;
  views: number;
  likes: number;
  comments: number;
  caption: string;
  thumbnail: string;
  submittedAt: Date;
  lastUpdated: Date;
  viewHistory: ViewSnapshot[];
}

export interface ViewSnapshot {
  timestamp: Date;
  views: number;
  likes: number;
  comments: number;
}

export interface User {
  id: string;
  username: string;
  email: string;
  totalViews: number;
  totalReels: number;
  payoutAmount: number;
  linkedAccounts: string[];
  paymentMethods: PaymentMethod;
  approved: boolean;
  createdAt: Date;
}

export interface PaymentMethod {
  usdt?: string;
  paypal?: string;
  upi?: string;
}

export interface AnalyticsData {
  totalViews: number;
  totalReels: number;
  viewGrowth: number;
  topPerformingReel: Reel | null;
  recentActivity: Reel[];
}