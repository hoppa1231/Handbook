import { Router } from 'express';
import { pool } from '../db/pool';

const router = Router();

type SupplierInput = {
  name?: string;
  address?: string;
  contact?: string;
  website?: string;
  rating?: number;
  nomenclature?: string;
  counterpartyType?: string;
  techAudit?: string;
  finAudit?: string;
  workExperience?: string;
};

router.get('/', async (_req, res, next) => {
  try {
    const { rows } = await pool.query(
      `select id, name, address, contact, website, rating,
              nomenclature,
              counterparty_type as "counterpartyType",
              tech_audit as "techAudit",
              fin_audit as "finAudit",
              work_experience as "workExperience"
       from suppliers
       order by name asc`
    );
    res.json(rows);
  } catch (error) {
    next(error);
  }
});

router.post('/', async (req, res, next) => {
  const {
    name,
    address,
    contact,
    website,
    rating,
    nomenclature,
    counterpartyType,
    techAudit,
    finAudit,
    workExperience
  }: SupplierInput = req.body ?? {};

  if (!name) {
    res.status(400).json({ message: 'Field "name" is required' });
    return;
  }

  try {
    const { rows } = await pool.query(
      `insert into suppliers (
         name, address, contact, website, rating,
         nomenclature, counterparty_type, tech_audit, fin_audit, work_experience
       )
       values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       returning id, name, address, contact, website, rating,
                 nomenclature,
                 counterparty_type as "counterpartyType",
                 tech_audit as "techAudit",
                 fin_audit as "finAudit",
                 work_experience as "workExperience"`,
      [
        name,
        address ?? null,
        contact ?? null,
        website ?? null,
        rating ?? null,
        nomenclature ?? null,
        counterpartyType ?? null,
        techAudit ?? null,
        finAudit ?? null,
        workExperience ?? null
      ]
    );

    res.status(201).json(rows[0]);
  } catch (error) {
    next(error);
  }
});

export default router;
