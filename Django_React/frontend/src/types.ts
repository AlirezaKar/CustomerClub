export type Gender = "male" | "female";

export interface ShopOption {
  id: number;
  name: string;
}

export interface ApiErrorPayload {
  error?: string;
  detail?: string;
  time?: number;
}

export interface Product {
  id: number;
  second_id: number;
  title: string;
  price: number;
  score: number;
  image_url?: string;
  is_offerable?: boolean;
  is_active: boolean;
  category_id?: number;
  category_title?: string;
}

export interface UserOffer {
  product: Product;
  offer_rate: number;
}

export interface UserProfile {
  first_name: string;
  last_name: string;
  phone_number: string;
  score: number;
  useroffer_set: UserOffer[];
}

export interface Category {
  id: number;
  title: string;
  description?: string | null;
  sort_order: number;
  is_active: boolean;
  products: Product[];
}

export interface CartLine {
  key: string;
  product: Product;
  quantity: number;
  offerRate: number;
  isSpecialOffer?: boolean;
}
