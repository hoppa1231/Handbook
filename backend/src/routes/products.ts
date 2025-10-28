import { Router } from 'express';
import { pool } from '../db/pool';

const router = Router();

type ProductInput = {
  partNumber?: string | number;
  name?: string;
  brand?: string;
  model?: string;
  serialNumber?: string | number;
  scheme?: string;
  posScheme?: string;
  material?: string;
  size?: string;
  comment?: string;
  category?: string;
};

router.get('/', async (_req, res, next) => {
  try {
    const { rows } = await pool.query(
      `select
         p.id,
         p.part_number as "partNumber",
         p.name,
         p.brand,
         p.model,
         p.serial_number as "serialNumber",
         p.scheme,
         p.pos_scheme as "posScheme",
         p.material,
         p.size,
         p.comment,
         p.category,
         pc.description as "categoryDescription"
       from products p
       left join product_categories pc on pc.code = p.category
       order by p.id desc`
    );
    res.json(rows);
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  const {
    partNumber,
    name,
    brand,
    model,
    serialNumber,
    scheme,
    posScheme,
    material,
    size,
    comment,
    category
  }: ProductInput = req.body ?? {};

  const partNumberValue =
    typeof partNumber === 'number'
      ? partNumber.toString()
      : typeof partNumber === 'string'
        ? partNumber.trim()
        : '';

  if (!partNumberValue) {
    res.status(400).json({ message: 'Field "partNumber" is required' });
    return;
  }

  if (!name) {
    res.status(400).json({ message: 'Field "name" is required' });
    return;
  }

  const serialNumberValue =
    typeof serialNumber === 'number'
      ? serialNumber
      : typeof serialNumber === 'string' && serialNumber.trim() !== ''
        ? Number.parseInt(serialNumber.trim(), 10)
        : null;

  if (typeof serialNumberValue === 'number' && Number.isNaN(serialNumberValue)) {
    res.status(400).json({ message: 'Field "serialNumber" must be an integer if provided' });
    return;
  }

  try {
    const { rows } = await pool.query(
      `insert into products (
        part_number,
        name,
        brand,
        model,
        serial_number,
        scheme,
        pos_scheme,
        material,
        size,
        comment,
        category
      ) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
      returning
        id,
        part_number as "partNumber",
        name,
        brand,
        model,
        serial_number as "serialNumber",
        scheme,
        pos_scheme as "posScheme",
        material,
        size,
        comment,
        category`,
      [
        partNumberValue,
        name,
        brand ?? null,
        model ?? null,
        serialNumberValue,
        scheme ?? null,
        posScheme ?? null,
        material ?? null,
        size ?? null,
        comment ?? null,
        category ?? null
      ]
    );

    res.status(201).json(rows[0]);
  } catch (error) {
    next(error);
  }
});

export default router;
