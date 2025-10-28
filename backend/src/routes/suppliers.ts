import { Router } from 'express';
import { pool } from '../db/pool';

const router = Router();

type SupplierInput = {
  name?: string;
  address?: string;
  contact?: string;
  website?: string;
  rating?: number;
};

router.get('/', async (_req, res, next) => {
  try {
    const { rows } = await pool.query(
      `select id, name, address, contact, website, rating
       from suppliers
       order by name asc`
    );
    res.json(rows);
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  const { name, address, contact, website, rating }: SupplierInput = req.body ?? {};

  if (!name) {
    res.status(400).json({ message: 'Field "name" is required' });
    return;
  }

  try {
    const { rows } = await pool.query(
      `insert into suppliers (name, address, contact, website, rating)
       values ($1, $2, $3, $4, $5)
       returning id, name, address, contact, website, rating`,
      [name, address ?? null, contact ?? null, website ?? null, rating ?? null]
    );

    res.status(201).json(rows[0]);
  } catch (error) {
    next(error);
  }
});

export default router;
